"""Provider-neutral model contract and OpenAI-compatible HTTP adapter."""

from __future__ import annotations

from abc import ABC, abstractmethod

import requests

from config.settings import AI_TIMEOUT_SECONDS, ModelSettings


class BaseAIModel(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate plain text from a prompt."""


class OpenAICompatibleModel(BaseAIModel):
    def __init__(self, settings: ModelSettings):
        self.settings = settings

    def generate(self, prompt: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key and self.settings.api_type.lower() not in {"ollama", "local"}:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        try:
            response = requests.post(
                f"{self.settings.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.settings.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                },
                timeout=AI_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise RuntimeError("AI үйлчилгээтэй холбогдох үед алдаа гарлаа эсвэл хугацаа хэтэрлээ.") from exc
        if not response.ok:
            raise RuntimeError(f"AI үйлчилгээ хүсэлтийг татгалзлаа (HTTP {response.status_code}).")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("AI үйлчилгээ хүлээгдсэн хариу буцаасангүй.") from exc
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("AI үйлчилгээ хоосон хариу буцаалаа.")
        return content