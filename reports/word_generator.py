"""Generate downloadable Word reports in memory."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from docx import Document
from docx.shared import Inches

from models.schemas import ReportContent
from reports.common import report_chart_images, report_data


def generate_word_report(
    analysis: dict[str, Any],
    insights: dict[str, Any],
    report: ReportContent | None = None,
    df=None,
    profile: dict[str, Any] | None = None,
) -> bytes:
    content = report_data(analysis, insights, report)
    document = Document()
    document.add_heading(content.title, 0)
    document.add_heading("Удирдлагын хураангуй", level=1)
    for item in content.executive_summary:
        document.add_paragraph(item, style="List Bullet")

    dataset = analysis["dataset"]
    document.add_heading("Өгөгдлийн ерөнхий мэдээлэл", level=1)
    info = document.add_table(rows=1, cols=2)
    info.style = "Light Shading Accent 1"
    info.rows[0].cells[0].text = "Үзүүлэлт"
    info.rows[0].cells[1].text = "Утга"
    for label, value in [
        ("Мөрийн тоо", f"{dataset['rows']:,}"),
        ("Баганын тоо", f"{dataset['columns']:,}"),
        ("Дутуу утга", f"{analysis['data_quality']['total_missing_values']:,}"),
        ("Давхардсан мөр", f"{analysis['data_quality']['duplicate_rows']:,}"),
    ]:
        cells = info.add_row().cells
        cells[0].text, cells[1].text = label, value

    if analysis["kpis"]:
        document.add_heading("KPI үзүүлэлтүүд", level=1)
        table = document.add_table(rows=1, cols=5)
        table.style = "Light Shading Accent 1"
        for cell, value in zip(table.rows[0].cells, ("Үзүүлэлт", "Нийт", "Дундаж", "Бага", "Их")):
            cell.text = value
        for item in analysis["kpis"]:
            row = table.add_row().cells
            for cell, value in zip(row, (
                item["column"], item["sum"], item["average"], item["minimum"], item["maximum"]
            )):
                cell.text = str(value)

    for title, image_buffer in report_chart_images(df, profile):
        document.add_heading(title, level=1)
        document.add_picture(image_buffer, width=Inches(6.2))
    for section in content.sections:
        document.add_heading(section.title, level=1)
        for paragraph in section.content.splitlines() or [""]:
            document.add_paragraph(paragraph)
    for heading, items in (("Дүгнэлт", content.conclusion), ("Дараагийн алхам / санал", content.recommendations)):
        document.add_heading(heading, level=1)
        for item in items:
            document.add_paragraph(item, style="List Bullet")
    output = BytesIO()
    document.save(output)
    return output.getvalue()