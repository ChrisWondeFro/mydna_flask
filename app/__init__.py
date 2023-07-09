from flask import Flask
from .views.main import dna_bp
from .models import db
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    app.register_blueprint(dna_bp)

    return app
