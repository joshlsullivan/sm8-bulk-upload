from pprint import pformat
from time import time

from flask import Flask, request, redirect,session, url_for, send_from_directory, render_template, flash
from werkzeug.utils import secure_filename
from flask.json import jsonify
import requests
from requests_oauthlib import OAuth2Session
import csv
import os

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/uploads')
ALLOWED_EXTENSIONS = set(['csv'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.urandom(24)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

client_id = '306550918970170'
client_secret = 'b3a8ed66bfb04ad8a7570d6cdd43946b'
redirect_uri = 'http://localhost:5000/callback'

authorization_base_url = 'https://go.servicem8.com/oauth/authorize'
token_url = 'https://go.servicem8.com/oauth/access_token'
refresh_url = token_url
scope = [
    'manage_jobs',
]

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    servicem8 = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)
    authorication_url, state = servicem8.authorization_url(authorization_base_url, access_type='offline', approval_prompt='force')
    session['oauth_state'] = state
    return redirect(authorication_url)


@app.route('/callback', methods=['GET'])
def callback():
    servicem8 = OAuth2Session(client_id, redirect_uri=redirect_uri, state=session['oauth_state'])
    token = servicem8.fetch_token(token_url, client_secret=client_secret, authorization_response=request.url)
    session['oauth_token'] = token
    print(token)
    return redirect(url_for('.success'))

@app.route("/success", methods=["GET"])
def success():
    return render_template('success.html', token=session['oauth_token'])

@app.route("/profile", methods=["GET"])
def profile():
    servicem8 = OAuth2Session(client_id, token=session['oauth_token'])
    return jsonify(servicem8.get('https://api.servicem8.com/api_1.0/job.json').json())

@app.route("/automatic_refresh", methods=["GET"])
def automatic_refresh():
    token = session['oauth_token']
    token['expires_at'] = time() - 10
    extra = {
        'client_id': client_id,
        'client_secret': client_secret,
    }
    def token_updater(token):
        session['oauth_token'] = token

    servicem8 = OAuth2Session(client_id,
                           token=token,
                           auto_refresh_kwargs=extra,
                           auto_refresh_url=refresh_url,
                           token_updater=token_updater)
    jsonify(servicem8.get('https://api.servicem8.com/api_1.0/job.json').json())
    return jsonify(session['oauth_token'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            with open(os.path.join(UPLOAD_FOLDER, filename)) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    print(row['company_uuid'], row['status'], row['job_description'])
                    servicem8 = OAuth2Session(client_id, token=session['oauth_token'])
                    servicem8.post('https://api.servicem8.com/api_1.0/job.json', data={"status":row['job_status'], "job_description":row['job_description'], "job_address":row['job_address'], "billing_address":row['billing_address']})
            #return redirect(url_for('uploaded_file',filename=filename))
            return render_template('file_upload_success.html', filename=filename)
    return render_template('upload.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)