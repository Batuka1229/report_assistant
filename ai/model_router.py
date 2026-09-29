"""Task-aware routing across configurable OpenAI-compatible model endpoints."""

from __future__ import annotations

import os

from ai.base_model import BaseAIModel, OpenAICompatibleModel
from config.settings import ModelSettings, configured_models

TASKS = {
    "DATA_ANALYSIS": "Өгөгдлийн ерөнхий шинжилгээ",
    "KPI_ANALYSIS": "KPI шинжилгээ",
    "TREND_ANALYSIS": "Хугацааны өөрчлөлт",
    "CATEGORY_COMPARISON": "Ангиллын харьцуулалт",
    "ANOMALY_ANALYSIS": "Онцгой утгын шинжилгээ",
    "CORRELATION_ANALYSIS": "Хамаарлын шинжилгээ",
    "EXECUTIVE_SUMMARY": "Удирдлагын хураангуй",
    "REPORT_WRITING": "Тайлан бичих",
}


class ModelRouter:
    def __init__(self, selected_provider: str | None = None):
        self.providers = configured_models()
        self.selected_provider = selected_provider

    def available_providers(self) -> list[str]:
        return list(self.providers)

    def get_model(self, task: str) -> BaseAIModel:
        if task not in TASKS:
            raise ValueError(f"Танигдаагүй AI даалгавар: {task}")
        provider_name = os.getenv(f"AI_{task}_PROVIDER", self.selected_provider or "default")
        settings = self.providers.get(provider_name)
        if settings is None:
            raise RuntimeError("AI загвар тохируулаагүй байна. .env файлд загварын endpoint болон нэрийг тохируулна уу.")
        model_name = os.getenv(f"AI_{task}_MODEL", settings.model)
        task_settings = ModelSettings(
            name=settings.name,
            base_url=os.getenv(f"AI_{task}_BASE_URL", settings.base_url).rstrip("/"),
            model=model_name,
            api_key=os.getenv(f"AI_{task}_API_KEY", settings.api_key),
            api_type=settings.api_type,
        )
        return OpenAICompatibleModel(task_settings)