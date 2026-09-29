from typing import Any

from ai.base_model import BaseAIModel
from ai.data_analyst import generate_validated
from ai.prompts import EXECUTIVE_ANALYST_PROMPT
from models.schemas import AIAnalysisResult


class ExecutiveAnalyst:
    def __init__(self, model: BaseAIModel):
        self.model = model

    def analyze(self, analysis: dict[str, Any]) -> AIAnalysisResult:
        return generate_validated(self.model, EXECUTIVE_ANALYST_PROMPT, analysis)