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
from config import Config
from datetime import datetime

app = Flask(__name__, static_url_path='', static_folder='app/static')
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

@dna_bp.route('/results')
async def results():
    
    report_generator = DNAReportGenerator(config.SQLALCHEMY_DATABASE_URI)

    summary_html, clinical_significance_counts = await report_generator.generate_report()

    return render_template('results.html', summary_html=summary_html, clinical_significance_counts=clinical_significance_counts)

@dna_bp.route('/home', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if 'dna_sequence' not in request.files:
            raise BadRequest("No file part in the request.")
        
        file = request.files['dna_sequence']
        if file.filename == '':
            return "No file selected for uploading."
        
        filename = secure_filename(file.filename)
        file_path =(os.path.join('/tmp', filename))
        file.save(file_path)

        image_url = url_for('static', filename='clinical_significance_distribution.png')

        report_generator = DNAReportGenerator(config.SQLALCHEMY_DATABASE_URI)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        summary_html, clinical_significance_counts = loop.run_until_complete(report_generator.generate_report(file_path, image_url))

        return render_template('results.html', summary_html=summary_html, clinical_significance_counts=clinical_significance_counts)

    return render_template('home_screen.html')

@dna_bp.route('/download_pdf')
def download_pdf():

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f'DNA_Health_Assessment_Report_{timestamp}.pdf'
    path_to_pdf = f'../{filename}'
    return send_file(path_to_pdf, as_attachment=True)

if __name__ == '__main__':
    from hypercorn.config import Config
    from hypercorn.asyncio import serve

    config = Config()
    config.bind = ["localhost:8000"]
    asyncio.run(serve(app, config))
