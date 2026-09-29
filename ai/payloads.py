"""Bounded, aggregate-only payloads sent to remote model providers."""

from __future__ import annotations

from typing import Any

from config.settings import MAX_CATEGORIES


def analysis_payload(analysis: dict[str, Any], task: str) -> dict[str, Any]:
    limit = max(1, MAX_CATEGORIES)
    dataset = analysis["dataset"]
    quality = analysis["data_quality"]
    common = {
        "dataset": dataset,
        "data_quality": quality,
        "column_roles": {
            key: analysis["profile"].get(key, [])
            for key in (
                "numeric_columns", "date_columns", "categorical_columns",
                "boolean_columns", "text_columns",
            )
        },
    }
    if task == "KPI_ANALYSIS":
        return {**common, "kpis": analysis["kpis"][:limit], "statistics": dict(
            list(analysis["statistics"].items())[:limit]
        )}
    if task == "TREND_ANALYSIS":
        return {
            **common,
            "trends": [
                {**trend, "periods": trend["periods"][-min(limit, 24):]}
                for trend in analysis["trends"][:10]
            ],
        }
    if task == "CATEGORY_COMPARISON":
        return {
            **common,
            "category_comparisons": [
                {**comparison, "categories": comparison["categories"][:limit]}
                for comparison in analysis["category_comparisons"][:limit]
            ],
        }
    if task == "ANOMALY_ANALYSIS":
        return {**common, "outliers": analysis["outliers"][:limit]}
    if task == "CORRELATION_ANALYSIS":
        return {**common, "correlations": analysis["correlations"][:limit]}
    if task == "EXECUTIVE_SUMMARY":
        return {
            **common,
            "kpis": analysis["kpis"][:limit],
            "statistics": dict(list(analysis["statistics"].items())[:limit]),
            "trends": [
                {**trend, "periods": trend["periods"][-min(limit, 12):]}
                for trend in analysis["trends"][:10]
            ],
            "category_comparisons": [
                {**comparison, "categories": comparison["categories"][:10]}
                for comparison in analysis["category_comparisons"][:10]
            ],
            "outliers": analysis["outliers"][:min(limit, 20)],
            "correlations": analysis["correlations"][:min(limit, 20)],
        }

    return {
        **common,
        "statistics": dict(list(analysis["statistics"].items())[:limit]),
        "kpis": analysis["kpis"][:limit],
        "trends": [
            {**trend, "periods": trend["periods"][-min(limit, 12):]}
            for trend in analysis["trends"][:10]
        ],
        "category_comparisons": [
            {**comparison, "categories": comparison["categories"][:10]}
            for comparison in analysis["category_comparisons"][:10]
        ],
        "outliers": analysis["outliers"][:min(limit, 20)],
        "correlations": analysis["correlations"][:min(limit, 20)],
    }
