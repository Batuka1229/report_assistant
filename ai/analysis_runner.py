"""Run selected AI interpretation tasks over deterministic analysis results."""

from __future__ import annotations

from typing import Any

from ai.anomaly_analyst import AnomalyAnalyst
from ai.data_analyst import DataAnalyst
from ai.executive_analyst import ExecutiveAnalyst
from ai.model_router import ModelRouter
from ai.trend_analyst import TrendAnalyst
from models.schemas import AIAnalysisResult

_TASK_CLASSES = {
    "DATA_ANALYSIS": DataAnalyst,
    "KPI_ANALYSIS": DataAnalyst,
    "TREND_ANALYSIS": TrendAnalyst,
    "CATEGORY_COMPARISON": DataAnalyst,
    "ANOMALY_ANALYSIS": AnomalyAnalyst,
    "CORRELATION_ANALYSIS": DataAnalyst,
    "EXECUTIVE_SUMMARY": ExecutiveAnalyst,
}


def run_ai_analysis(
    analysis: dict[str, Any],
    selected_tasks: list[str],
    router: ModelRouter,
) -> dict[str, AIAnalysisResult]:
    results: dict[str, AIAnalysisResult] = {}
    for task in selected_tasks:
        analyst_type = _TASK_CLASSES.get(task)
        if analyst_type is None:
            raise ValueError(f"AI шинжилгээний даалгавар дэмжигдэхгүй байна: {task}")
        model = router.get_model(task)
        if analyst_type is DataAnalyst:
            results[task] = DataAnalyst(model, task).analyze(analysis)
        else:
            results[task] = analyst_type(model).analyze(analysis)
    return results


def aggregate_insights(results: dict[str, AIAnalysisResult]) -> dict[str, Any]:
    return {
        "summary": [item for result in results.values() for item in result.summary],
        "insights": [
            insight.model_dump()
            for result in results.values()
            for insight in result.insights
        ],
        "recommendations": list(dict.fromkeys(
            recommendation
            for result in results.values()
            for recommendation in result.recommendations
        )),
    }