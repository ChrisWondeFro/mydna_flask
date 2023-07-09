import pandas as pd
import matplotlib.pyplot as plt

class DataVisualizer:
    @staticmethod
    def generate_plot(report):
        df = pd.DataFrame(report)
        df['clinicalsignificance'].value_counts().plot(kind='pie', autopct='%1.1f%%')
        plt.title('Distribution of Clinical Significance')
        plt.savefig("clinical_significance_distribution.png")
        plt.clf()
