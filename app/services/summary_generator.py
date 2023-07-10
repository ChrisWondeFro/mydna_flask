from jinja2 import Environment, FileSystemLoader
import pandas as pd

env = Environment(loader=FileSystemLoader('app/templates'))

class SummaryGenerator:
    @staticmethod
    def generate_summary(variant_info, clinical_significance_counts):
        template = env.get_template('summary_template.html')
        summary_html = template.render(variant_info=variant_info, clinical_significance_counts=clinical_significance_counts)
        return summary_html
