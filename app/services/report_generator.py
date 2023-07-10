
from app.services.file_reader import read_and_validate_data
from app.utils.ensemblutils import EnsemblAPI, DataProcessor
from app.utils.ncbiutils import ApiClient
from app.services.dao import VariantDAO
from app.services.data_visualizer import DataVisualizer
from app.services.summary_generator import SummaryGenerator
from app.services.pdf_generator import PDFGenerator
from collections import Counter

class DNAReportGenerator:
    def __init__(self, connection_string):
        self.variant_dao = VariantDAO(connection_string)
        self.data_visualizer = DataVisualizer()
        self.summary_generator = SummaryGenerator()
        self.pdf_generator = PDFGenerator()

    async def generate_report(self, file_path):
        self.data = read_and_validate_data(file_path)
        ids = [int(rsid) for rsid in self.data['rsid'].tolist()]
        variant_info = self.variant_dao.get_variant_info(ids)
        self.data_visualizer.generate_plot(variant_info)
        clinical_significance_counts = Counter([variant['clinicalsignificance'] for variant in variant_info])
        summary_html = self.summary_generator.generate_summary(variant_info, clinical_significance_counts)
        self.pdf_generator.write_report(summary_html)  
        clinical_significance_counts = Counter([variant['clinicalsignificance'] for variant in variant_info])
        return summary_html, clinical_significance_counts      

