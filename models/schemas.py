"""Validated contracts for AI outputs and report content."""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel, Field, ValidationError


class Insight(BaseModel):
    title: str
    description: str
    importance: str | None = None


class AIAnalysisResult(BaseModel):
    summary: list[str] = Field(default_factory=list)
    insights: list[Insight] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ReportSection(BaseModel):
    title: str
    content: str


class ReportContent(BaseModel):
    title: str = "Өгөгдлийн шинжилгээний тайлан"
    executive_summary: list[str] = Field(default_factory=list)
    sections: list[ReportSection] = Field(default_factory=list)
    conclusion: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class AIOutputError(ValueError):
    """Raised when a model response cannot be parsed or validated."""


SchemaModel = TypeVar("SchemaModel", bound=BaseModel)


def parse_model_json(text: str, schema: type[SchemaModel]) -> SchemaModel:
    candidate = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1)
    try:
        payload: Any = json.loads(candidate)
        return schema.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise AIOutputError(f"Моделын хариу шаардлагатай JSON бүтэцтэй таарахгүй байна: {exc}") from exc