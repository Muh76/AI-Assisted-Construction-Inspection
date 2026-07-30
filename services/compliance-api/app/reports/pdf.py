from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas import ComplianceReport


def build_compliance_pdf(report: ComplianceReport, project_name: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"Compliance Report: {project_name}", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Project ID: {report.project_id}", styles["Normal"]),
        Paragraph(f"Generated: {report.generated_at.isoformat()}", styles["Normal"]),
        Paragraph(
            f"Summary: {report.summary.passed} passed, {report.summary.failed} failed",
            styles["Normal"],
        ),
        Spacer(1, 18),
    ]

    table_data = [["Rule ID", "Citation", "Passed", "Message"]]
    for result in report.results:
        table_data.append(
            [
                result.rule_id,
                result.regulation_citation or "—",
                "Yes" if result.passed else "No",
                result.message,
            ]
        )

    table = Table(table_data, colWidths=[100, 80, 50, 330], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)

    doc.build(story)
    return buffer.getvalue()
