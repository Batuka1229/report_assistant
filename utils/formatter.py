"""Presentation helpers for report output."""

from __future__ import annotations

from typing import Any

from models.schemas import ReportContent, ReportSection


def build_report_content(
    analysis: dict[str, Any],
    insights: dict[str, Any],
    generated: ReportContent | None = None,
) -> ReportContent:
    if generated is not None:
        return generated

    dataset = analysis["dataset"]
    summary = [
        f"Шинжилгээнд {dataset['rows']:,} мөр, {dataset['columns']:,} багана бүхий өгөгдөл хамрагдав."
    ]
    if analysis["data_quality"]["total_missing_values"]:
        summary.append(f"Дутуу утгын нийт тоо: {analysis['data_quality']['total_missing_values']:,}.")
    else:
        summary.append("Шалгасан өгөгдөлд дутуу утга илрээгүй.")
    sections = [
        ReportSection(title="Тайлангийн зорилго", content=(
            "Өгөгдөлд Pandas болон NumPy ашиглан тооцсон үзүүлэлтүүдийг нэгтгэн, "
            "өгөгдлийн чанар, гол KPI болон ажиглагдсан өөрчлөлтийг танилцуулах."
        )),
        ReportSection(title="Өгөгдлийн ерөнхий мэдээлэл", content=(
            f"Мөрийн тоо: {dataset['rows']:,}; баганын тоо: {dataset['columns']:,}. "
            f"Давхардсан мөр: {analysis['data_quality']['duplicate_rows']:,}; "
            f"дутуу утга: {analysis['data_quality']['total_missing_values']:,}."
        )),
        ReportSection(title="Гол үзүүлэлтүүд", content="\n".join(
            f"{item['column']}: нийт {item['sum']}, дундаж {item['average']}, "
            f"хамгийн бага {item['minimum']}, хамгийн их {item['maximum']}."
            for item in analysis["kpis"]
        ) or "Тооцоолох боломжтой KPI үзүүлэлт илрээгүй."),
        ReportSection(title="Үндсэн шинжилгээ", content="\n".join(
            f"{column}: дундаж {values['mean']}, медиан {values['median']}, "
            f"стандарт хазайлт {values['std']}."
            for column, values in analysis["statistics"].items()
        ) or "Тоон багана илрээгүй."),
        ReportSection(title="Хугацааны өөрчлөлт", content=(
            "\n".join(
                f"{item['date_column']} / {item['value_column']} ({item['frequency']}): "
                f"{item['period_count']} хугацаа; хамгийн өндөр нь {item['highest_period']}, "
                f"хамгийн бага нь {item['lowest_period']}; нийт өөрчлөлт {item['total_change_percent']}%."
                for item in analysis["trends"][:10]
            ) if analysis["trends"] else "Хангалттай огнооны мэдээлэлтэй хугацааны цуваа илрээгүй."
        )),
        ReportSection(title="Харьцуулсан шинжилгээ", content=(
            "\n".join(
                f"{item['category_column']} / {item['metric_column']}: " + "; ".join(
                    f"{category['category']} — нийлбэр {category['sum']}, дундаж {category['average']}, "
                    f"нийт дүнд эзлэх хувь {category['percentage_of_total']}%"
                    for category in item["categories"][:5]
                )
                for item in analysis["category_comparisons"][:10]
            ) if analysis["category_comparisons"] else "Харьцуулах боломжтой ангилал илрээгүй."
        )),
        ReportSection(title="Анхаарах үзүүлэлтүүд", content=(
            f"{len(analysis['outliers'])} ердийн түвшнээс мэдэгдэхүйц ялгаатай утга илэрсэн. "
            "Эдгээр утгыг алдаа гэж шууд үзэхгүй.\n" + "\n".join(
                f"{item['column']} баганын {item['row_index']} мөрийн утга {item['value']} "
                f"(хязгаар {item['lower_bound']}–{item['upper_bound']})."
                for item in analysis["outliers"][:10]
            )
        )),
        ReportSection(title="Хамаарлын шинжилгээ", content=(
            "\n".join(
                f"{item['column_a']} ба {item['column_b']}: {item['correlation']} "
                f"({item['strength']} {item['direction']} хамаарал). Хамаарал нь шалтгааныг тогтоохгүй."
                for item in analysis["correlations"][:10]
            ) if analysis["correlations"] else "Хоёр ба түүнээс олон тохирох тоон багана илрээгүй."
        )),
        ReportSection(title="AI-аар тодорхойлсон гол insights", content="\n".join(
            f"{item['title']}: {item['description']}" for item in insights.get("insights", [])
        ) or "AI шинжилгээ ажиллуулаагүй."),
    ]
    return ReportContent(
        executive_summary=insights.get("summary") or summary,
        sections=sections,
        conclusion=summary,
        recommendations=insights.get("recommendations", []),
    )