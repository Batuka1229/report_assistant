from typing import Any

from ai.base_model import BaseAIModel
from ai.data_analyst import generate_validated
from ai.prompts import REPORT_WRITER_PROMPT
from models.schemas import ReportContent


class AIReportWriter:
    def __init__(self, model: BaseAIModel):
        self.model = model

    def write(self, analysis: dict[str, Any], insights: dict[str, Any]) -> ReportContent:
        from ai.payloads import analysis_payload

        return generate_validated(
            self.model,
            REPORT_WRITER_PROMPT,
            {"analysis": analysis_payload(analysis, "REPORT_WRITING"), "insights": insights},
            ReportContent,
        )