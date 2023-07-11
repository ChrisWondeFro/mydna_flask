
from jinja2 import Environment, FileSystemLoader
from flask import render_template, current_app

env = Environment(loader=FileSystemLoader('app/templates'))


def generate_summary_data(self, organized_data):
    summary_data = []
    total_variants = sum(len(v) for cs in organized_data.values() for t in cs.values() for v in t)
    summary_data.append(f"A total of {total_variants} variants were analyzed.")

    for cs, types in organized_data.items():
        cs_count = sum(len(v) for t in types.values() for v in t)
        summary_data.append(f"{cs_count} variants were found to be {cs}.")

    return summary_data

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
