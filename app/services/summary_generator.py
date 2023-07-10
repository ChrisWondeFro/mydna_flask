from jinja2 import Environment, FileSystemLoader
import pandas as pd

env = Environment(loader=FileSystemLoader('app/templates'))

class SummaryGenerator:
    @staticmethod
    def generate_summary(variant_info, clinical_significance_counts, image_url):
        template = env.get_template('summary_template.html')
        summary_html = template.render(
            variant_info=variant_info, 
            clinical_significance_counts=clinical_significance_counts, 
            image_url="http://localhost:8000/static/clinical_significance_distribution.png"
        )
        return summary_html
