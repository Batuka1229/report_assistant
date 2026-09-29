"""Generate multi-sheet Excel analysis reports in memory."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from models.schemas import ReportContent
from reports.common import report_data


def _safe_frame(rows: list[dict[str, Any]], columns: list[str] | None = None) -> pd.DataFrame:
    frame = pd.DataFrame.from_records(rows, columns=columns)
    for column in frame.columns:
        if pd.api.types.is_object_dtype(frame[column]) or pd.api.types.is_string_dtype(frame[column]):
            frame[column] = frame[column].map(
                lambda value: "'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@"))
                else value
            )
    return frame


def generate_excel_report(
    analysis: dict[str, Any],
    insights: dict[str, Any],
    report: ReportContent | None = None,
) -> bytes:
    content = report_data(analysis, insights, report)
    dataset = analysis["dataset"]
    summary = [
        {"Үзүүлэлт": "Мөрийн тоо", "Утга": dataset["rows"]},
        {"Үзүүлэлт": "Баганын тоо", "Утга": dataset["columns"]},
        {"Үзүүлэлт": "Дутуу утгын тоо", "Утга": analysis["data_quality"]["total_missing_values"]},
        {"Үзүүлэлт": "Давхардсан мөр", "Утга": analysis["data_quality"]["duplicate_rows"]},
        *({"Үзүүлэлт": "Тайлангийн хураангуй", "Утга": line} for line in content.executive_summary),
    ]
    kpis = analysis["kpis"]
    statistics = [
        {"Багана": column, **values}
        for column, values in analysis["statistics"].items()
    ]
    trends = [
        {
            "огнооны_багана": item["date_column"],
            "үзүүлэлтийн_багана": item["value_column"],
            "давтамж": item["frequency"],
            **period,
        }
        for item in analysis["trends"]
        for period in item["periods"]
    ]
    comparisons = [
        {
            "ангиллын_багана": item["category_column"],
            "үзүүлэлтийн_багана": item["metric_column"],
            **category,
        }
        for item in analysis["category_comparisons"]
        for category in item["categories"]
    ]
    ai_rows = [
        {"Төрөл": "Хураангуй", "Гарчиг": "", "Агуулга": line}
        for line in insights.get("summary", [])
    ]
    ai_rows.extend(
        {"Төрөл": "Insight", "Гарчиг": item.get("title", ""), "Агуулга": item.get("description", "")}
        for item in insights.get("insights", [])
    )
    ai_rows.extend(
        {"Төрөл": "Санал", "Гарчиг": "", "Агуулга": item}
        for item in insights.get("recommendations", [])
    )

    sheets = {
        "Summary": _safe_frame(summary),
        "KPI": _safe_frame(kpis, ["column", "sum", "average", "median", "minimum", "maximum", "count"]),
        "Statistics": _safe_frame(statistics),
        "Trend": _safe_frame(trends),
        "Category Comparison": _safe_frame(comparisons),
        "Outliers": _safe_frame(analysis["outliers"]),
        "Correlation": _safe_frame(analysis["correlations"]),
        "AI Insights": _safe_frame(ai_rows, ["Төрөл", "Гарчиг", "Агуулга"]),
    }
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes = "A2"
            if worksheet.max_column:
                worksheet.auto_filter.ref = worksheet.dimensions
                for column_cells in worksheet.columns:
                    max_length = min(max((len(str(cell.value or "")) for cell in column_cells), default=0), 50)
                    worksheet.column_dimensions[column_cells[0].column_letter].width = max(12, max_length + 2)
    return output.getvalue()