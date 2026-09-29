"""Environment-backed application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

MAX_CATEGORIES = int(os.getenv("MAX_CATEGORIES", "50"))
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "45"))
AI_RETRIES = max(0, min(3, int(os.getenv("AI_RETRIES", "1"))))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))


@dataclass(frozen=True)
class ModelSettings:
    name: str
    base_url: str
    model: str
    api_key: str = ""
    api_type: str = "openai-compatible"


def configured_models() -> dict[str, ModelSettings]:
    """Return configured OpenAI-compatible endpoints without exposing credentials."""
    names = [part.strip() for part in os.getenv("AI_PROVIDERS", "default").split(",") if part.strip()]
    providers: dict[str, ModelSettings] = {}
    for name in names:
        prefix = "AI" if name == "default" else f"AI_{name.upper().replace('-', '_')}"
        base_url = os.getenv(f"{prefix}_BASE_URL", "").strip().rstrip("/")
        model = os.getenv(f"{prefix}_MODEL", "").strip()
        if not base_url or not model:
            continue
        providers[name] = ModelSettings(
            name=name,
            base_url=base_url,
            model=model,
            api_key=os.getenv(f"{prefix}_API_KEY", ""),
            api_type=os.getenv(f"{prefix}_API_TYPE", "openai-compatible"),
        )
    return providers
