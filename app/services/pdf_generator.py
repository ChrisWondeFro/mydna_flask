from reportlab.pdfgen import canvas

class PDFGenerator:
    def write_report(self, summary_html):
        c = canvas.Canvas("DNA_Health_Assessment_Report.pdf")
        textobject = c.beginText()
        textobject.setTextOrigin(10, 730)
        lines = summary_html.split('\n')
        for line in lines:
            textobject.textLine(line.strip())
        c.drawText(textobject)
        c.save()