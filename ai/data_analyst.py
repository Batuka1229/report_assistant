"""Validated analysis task runner."""

from __future__ import annotations

import json
import logging
from typing import Any, TypeVar

from pydantic import BaseModel

from ai.base_model import BaseAIModel
from config.settings import AI_RETRIES
from models.schemas import AIAnalysisResult, AIOutputError, parse_model_json

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def generate_validated(
    model: BaseAIModel,
    system_prompt: str,
    payload: dict[str, Any],
    schema: type[T] = AIAnalysisResult,
) -> T:
    request = (
        f"{system_prompt}\n\nШИНЖИЛГЭЭНИЙ ӨГӨГДӨЛ (JSON):\n"
        f"{json.dumps(payload, ensure_ascii=False, allow_nan=False, default=str)}"
    )
    last_error: AIOutputError | None = None
    for attempt in range(AI_RETRIES + 1):
        response = model.generate(request)
        try:
            return parse_model_json(response, schema)
        except AIOutputError as exc:
            last_error = exc
            logger.warning("AI output validation failed (attempt %s of %s).", attempt + 1, AI_RETRIES + 1)
            request += "\nӨмнөх хариу JSON схемд нийцээгүй. Зөвхөн шаардлагатай схемээр дахин хариул."
    if last_error is not None:
        raise last_error
    raise RuntimeError("AI хариуг баталгаажуулах боломжгүй байна.")
from ai.prompts import DATA_ANALYST_PROMPT


class DataAnalyst:
    def __init__(self, model: BaseAIModel, task: str = "DATA_ANALYSIS"):
        self.model = model
        self.task = task

    def analyze(self, analysis: dict[str, Any]) -> AIAnalysisResult:
        from ai.payloads import analysis_payload

        return generate_validated(
            self.model,
            DATA_ANALYST_PROMPT,
            analysis_payload(analysis, self.task),
        )