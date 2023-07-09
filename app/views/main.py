import logging
from flask.logging import default_handler
logger = logging.getLogger(__name__)
stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)
from flask import Flask, Blueprint, request, render_template, jsonify, send_file, redirect, url_for
from werkzeug.exceptions import BadRequest, Unauthorized
from werkzeug.utils import secure_filename
from flask_compress import Compress
import firebase_admin
from firebase_admin import credentials, auth
import asyncio
import os

from app.services.report_generator import DNAReportGenerator 
from app.services.file_reader import read_and_validate_data
from config import Config

app = Flask(__name__)
Compress(app)

config = Config()

firebase_credentials = {
    "type": config.FIREBASE_TYPE,
    "project_id": config.FIREBASE_PROJECT_ID,
    "private_key_id": config.FIREBASE_PRIVATE_KEY_ID,
    "private_key": config.FIREBASE_PRIVATE_KEY.replace("\\n", "\n"),
    "client_email": config.FIREBASE_CLIENT_EMAIL,
    "client_id": config.FIREBASE_CLIENT_ID,
    "auth_uri": config.FIREBASE_AUTH_URI,
    "token_uri": config.FIREBASE_TOKEN_URI,
    "auth_provider_x509_cert_url": config.FIREBASE_AUTH_PROVIDER_X509_CERT_URL,
    "client_x509_cert_url": config.FIREBASE_CLIENT_X509_CERT_URL,
}

cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred)

report_generator = DNAReportGenerator

dna_bp = Blueprint('dna', __name__)

@app.errorhandler(BadRequest)
def handle_bad_request(e):
    return jsonify({"error": str(e)}), 400

@app.errorhandler(Unauthorized)
def handle_unauthorized(e):
    return jsonify({"error": str(e)}), 401

@dna_bp.route('/', methods=['GET'])
def auth():
    return render_template('auth.html')

@dna_bp.route('/home', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if 'file' not in request.files:
            raise BadRequest("No file part in the request.")
        
        if file.filename == '':
              return "No file selected for uploading."
         
        file = request.files['file']
        file = f"/tmp/dna_file{os.path.splitext(file.filename)[1]}"

        filename = secure_filename(file.filename)
        file.save(filename)
        filename = read_and_validate_data(file)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        report = loop.run_until_complete(report_generator.read_and_validate(secure_filename))

        return render_template('results.html', report=report)

    return render_template('home_screen.html')


if __name__ == '__main__':
    from hypercorn.config import Config
    from hypercorn.asyncio import serve

    config = Config()
    config.bind = ["localhost:8000"]
    asyncio.run(serve(app, config))
