from app.services.file_reader import read_and_validate_data
from app.utils.ensemblutils import EnsemblAPI, DataProcessor
from app.utils.ncbiutils import ApiClient
from app.services.dao import VariantDAO
from app.services.data_visualizer import DataVisualizer
from app.services.summary_generator import SummaryGenerator
from app.services.pdf_generator import PDFGenerator

class DNAReportGenerator:
    def __init__(self, connection_string):
        self.data = read_and_validate_data
        self.variant_dao = VariantDAO(connection_string)
        self.data_visualizer = DataVisualizer()
        self.summary_generator = SummaryGenerator()
        self.pdf_generator = PDFGenerator()

    async def generate_report(self):
        ids = [int(rsid) for rsid in self.data['rsid'].tolist()]   
        variant_info = self.variant_dao.get_variant_info(ids)
        self.data_visualizer.generate_plot(variant_info)
        summary = self.summary_generator.generate_summary(variant_info)
        # Generate PDF with self.pdf_generator