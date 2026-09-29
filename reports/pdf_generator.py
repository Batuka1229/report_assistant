"""Generate downloadable PDF reports in memory."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models.schemas import ReportContent
from reports.common import report_chart_images, report_data


def _register_mongolian_font() -> str | None:
    try:
        pdfmetrics.getFont("ReportUnicode")
        return "ReportUnicode"
    except KeyError:
        pass
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
        Path("C:/Windows/Fonts/tahoma.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            pdfmetrics.registerFont(TTFont("ReportUnicode", str(candidate)))
            return "ReportUnicode"
    return None


def generate_pdf_report(
    analysis: dict[str, Any],
    insights: dict[str, Any],
    report: ReportContent | None = None,
    df=None,
    profile: dict[str, Any] | None = None,
) -> bytes:
    content = report_data(analysis, insights, report)
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
                                 topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    font_name = _register_mongolian_font()
    if font_name:
        for style_name in ("Normal", "Title", "Heading1", "Heading2"):
            styles[style_name].fontName = font_name
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], alignment=TA_CENTER, spaceAfter=14)
    body_style = styles["BodyText"]
    story = [Paragraph(escape(content.title), title_style), Spacer(1, 6)]

    def add_section(title: str, paragraphs: list[str]) -> None:
        story.append(Paragraph(escape(title), styles["Heading2"]))
        for paragraph in paragraphs:
            for line in str(paragraph).splitlines() or [""]:
                story.append(Paragraph(escape(line), body_style))
                story.append(Spacer(1, 4))

    add_section("Удирдлагын хураангуй", content.executive_summary)
    dataset = analysis["dataset"]
    dataset_table = Table([
        ["Өгөгдөл", "Утга"],
        ["Мөрийн тоо", f"{dataset['rows']:,}"],
        ["Баганын тоо", f"{dataset['columns']:,}"],
        ["Дутуу утга", f"{analysis['data_quality']['total_missing_values']:,}"],
        ["Давхардсан мөр", f"{analysis['data_quality']['duplicate_rows']:,}"],
    ], colWidths=[65 * mm, 85 * mm])
    dataset_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#164E63")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("FONTNAME", (0, 0), (-1, -1), font_name or "Helvetica"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([Paragraph("Өгөгдлийн ерөнхий мэдээлэл", styles["Heading2"]), dataset_table])

    if analysis["kpis"]:
        story.append(Paragraph("KPI үзүүлэлтүүд", styles["Heading2"]))
        rows = [["Үзүүлэлт", "Нийт", "Дундаж", "Бага", "Их"]]
        rows.extend([[str(item["column"]), str(item["sum"]), str(item["average"]),
                      str(item["minimum"]), str(item["maximum"])] for item in analysis["kpis"]])
        table = Table(rows, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#164E63")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), font_name or "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        story.append(table)

    for title, image_buffer in report_chart_images(df, profile):
        story.append(Paragraph(title, styles["Heading2"]))
        story.append(Image(image_buffer, width=165 * mm, height=75 * mm, kind="proportional"))
    for section in content.sections:
        add_section(section.title, [section.content])
    add_section("Дүгнэлт", content.conclusion)
    add_section("Дараагийн алхам / санал", content.recommendations)
    document.build(story)
    return buffer.getvalue()