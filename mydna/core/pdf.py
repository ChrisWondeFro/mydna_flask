"""Render a report to PDF, in memory.

The previous implementation dumped raw HTML source lines onto a canvas at a
hardcoded absolute path under the original author's home directory, and cached
the last filename on a class attribute shared by every request.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from mydna.core.report import Report

DISCLAIMER = (
    "This report is for informational and educational purposes only. It is not "
    "medical advice, not a diagnosis, and not a risk prediction. It reports what "
    "the public ClinVar database already records about variants present in your "
    "file. Consumer genotyping arrays produce false positives, and a ClinVar "
    "entry does not mean you have or will develop a condition. Discuss any "
    "concerns with a qualified clinician or genetic counsellor."
)

# Cap per group: a full export can match tens of thousands of records, and an
# unbounded PDF is neither useful nor renderable in reasonable time.
MAX_ROWS_PER_GROUP = 100


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("MyDnaTitle", parent=base["Title"], fontSize=20, spaceAfter=6),
        "heading": ParagraphStyle(
            "MyDnaHeading",
            parent=base["Heading2"],
            fontSize=13,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "subheading": ParagraphStyle(
            "MyDnaSubheading",
            parent=base["Heading3"],
            fontSize=11,
            spaceBefore=8,
            spaceAfter=4,
            textColor=colors.HexColor("#444444"),
        ),
        "body": ParagraphStyle("MyDnaBody", parent=base["BodyText"], fontSize=9.5, leading=13.5),
        "small": ParagraphStyle(
            "MyDnaSmall",
            parent=base["BodyText"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#666666"),
            alignment=TA_LEFT,
        ),
    }


def render_report_pdf(report: Report) -> BytesIO:
    """Build the PDF and return a rewound buffer ready to stream."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title="MyDNA variant report",
        author="MyDNA",
    )
    style = _styles()
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    story: list = [
        Paragraph("MyDNA variant report", style["title"]),
        Paragraph(f"Generated {escape(generated)}", style["small"]),
        Spacer(1, 10),
        HRFlowable(width="100%", color=colors.HexColor("#dddddd")),
        Paragraph("Important", style["heading"]),
        Paragraph(escape(DISCLAIMER), style["body"]),
        Paragraph("Summary", style["heading"]),
    ]

    summary = [
        f"{report.parse.total_rows:,} rows read from your file "
        f"({escape(report.parse.detected_format)} format).",
        f"{report.rsids_submitted:,} unique dbSNP identifiers extracted.",
        f"{report.matched_rsids:,} of them appear in ClinVar, "
        f"matching {report.matched_records:,} records.",
    ]
    if report.parse.skipped_internal:
        summary.append(
            f"{report.parse.skipped_internal:,} internal probe identifiers were "
            "skipped; these are not dbSNP variants."
        )
    story.append(
        ListFlowable(
            [ListItem(Paragraph(line, style["body"])) for line in summary],
            bulletType="bullet",
            leftIndent=14,
        )
    )

    if report.index_metadata.get("clinvar_last_modified"):
        story.append(
            Paragraph(
                f"ClinVar release: {escape(report.index_metadata['clinvar_last_modified'])}",
                style["small"],
            )
        )

    story.append(Paragraph("Breakdown by classification", style["heading"]))
    story.append(
        ListFlowable(
            [
                ListItem(
                    Paragraph(
                        f"<b>{escape(group.label)}</b>: {group.count:,} records",
                        style["body"],
                    )
                )
                for group in report.groups
            ],
            bulletType="bullet",
            leftIndent=14,
        )
    )

    for group in report.groups:
        story.append(PageBreak())
        story.append(Paragraph(escape(group.label), style["heading"]))
        story.append(Paragraph(f"{group.count:,} records in this category.", style["small"]))

        for type_group in group.types:
            story.append(
                Paragraph(
                    f"{escape(type_group.label)} ({type_group.count:,})",
                    style["subheading"],
                )
            )
            for variant in type_group.variants[:MAX_ROWS_PER_GROUP]:
                gene = f" &middot; {escape(variant.gene_symbol)}" if variant.gene_symbol else ""
                stars = "\u2605" * variant.review_stars + "\u2606" * (4 - variant.review_stars)
                conditions = "; ".join(variant.conditions) or "No condition listed"
                story.append(
                    Paragraph(
                        f"<b>{escape(variant.rsid_label)}</b>{gene} &middot; "
                        f"{escape(stars)}<br/>{escape(conditions)}",
                        style["body"],
                    )
                )
            if type_group.count > MAX_ROWS_PER_GROUP:
                story.append(
                    Paragraph(
                        f"...and {type_group.count - MAX_ROWS_PER_GROUP:,} more "
                        "(see the full report in your browser).",
                        style["small"],
                    )
                )

    story.append(PageBreak())
    story.append(Paragraph("Data source", style["heading"]))
    story.append(
        Paragraph(
            "Variant classifications are from ClinVar, a public archive maintained "
            "by the National Center for Biotechnology Information (NCBI), U.S. "
            "National Library of Medicine. Landrum MJ, et al. ClinVar: improving "
            "access to variant interpretations and supporting evidence. Nucleic "
            "Acids Research. 2018;46(D1):D1062-D1067.",
            style["small"],
        )
    )

    document.build(story)
    buffer.seek(0)
    return buffer
