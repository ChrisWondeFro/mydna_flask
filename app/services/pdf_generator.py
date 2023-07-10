from reportlab.pdfgen import canvas
from datetime import datetime

class PDFGenerator:
    def write_report(self, summary_html):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'DNA_Health_Assessment_Report_{timestamp}.pdf'

        c = canvas.Canvas(filename)
        textobject = c.beginText()
        textobject.setTextOrigin(10, 730)
        lines = summary_html.split('\n')
        for line in lines:
            textobject.textLine(line.strip())
        c.drawText(textobject)
        c.save()

        return filename
