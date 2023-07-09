import pandas as pd

class SummaryGenerator:
    @staticmethod
    def generate_summary(risk_assessment):
        summary_text = f"""
        Summary
        A total of {len(risk_assessment)} variants were analyzed.
        """
        clinical_significance_counts = dict(pd.DataFrame(risk_assessment)['clinicalsignificance'].value_counts())
        for significance, count in clinical_significance_counts.items():
            summary_text += f"<p>{count} variants were found to be {significance}.</p>"
        return summary_text
