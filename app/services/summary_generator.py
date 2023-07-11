
from jinja2 import Environment, FileSystemLoader
from flask import render_template, current_app

env = Environment(loader=FileSystemLoader('app/templates'))

class SummaryGenerator:
    @staticmethod
    def generate_summary(organized_data, clinical_significance_counts, image_url):
        with current_app.app_context():
            summary_html = render_template(
                'summary_template.html',
                clinical_significances=organized_data, 
                clinical_significance_counts=clinical_significance_counts, 
                image_url="http://localhost:8000/static/clinical_significance_distribution.png"
            )
        return summary_html
