from typing import Any

from ai.base_model import BaseAIModel
from ai.data_analyst import generate_validated
from ai.prompts import TREND_ANALYST_PROMPT
from models.schemas import AIAnalysisResult


class TrendAnalyst:
    def __init__(self, model: BaseAIModel):
        self.model = model

    def analyze(self, analysis: dict[str, Any]) -> AIAnalysisResult:
        return generate_validated(self.model, TREND_ANALYST_PROMPT, {
            "dataset": analysis["dataset"], "trends": analysis["trends"]
        })