"""Ollama API connector."""

from __future__ import annotations

import json
import logging

import httpx

from src.config import get_settings
from src.connectors.llm.base import BusinessContext, ConnectorError, LLMConnector, PitchResult

logger = logging.getLogger(__name__)


def _build_prompt(context: BusinessContext, preset: dict | None = None) -> str:
    """Build Ollama prompt text from business context."""
    preset = preset or {}
    issues = ", ".join(context.website_issues) if context.website_issues else "none"
    tone = preset.get("tone")
    tone_instruction = f" Use a {tone} tone." if tone else ""
    return (
        f"Business: {context.name} in {context.city}\n"
        f"Type: {context.business_type}\n"
        f"Years in business: {context.years_in_business or 'unknown'}\n"
        f"Has website: {context.has_website}\n"
        f"Website score: {context.website_score or 'none'}\n"
        f"Website issues: {issues}\n"
        f"Maturity stage: {context.maturity_stage or 'unknown'}\n\n"
        "Generate a personalized business pitch as JSON with these exact keys:\n"
        "- pitch_text: the outreach message\n"
        "- membership_idea: a recurring revenue idea for this business\n"
        "- website_benefits: bullet points on how a new website helps\n"
        "- model_used: set to 'ollama'\n\n"
        f"Return ONLY valid JSON.{tone_instruction}"
    )


class OllamaConnector(LLMConnector):
    """Connector for Ollama local HTTP API."""

    def __init__(self, model: str | None = None) -> None:
        self.settings = get_settings()
        self.model = model or self.settings.ollama_model

    def generate_pitch(self, context: BusinessContext, preset: dict | None = None) -> PitchResult:
        """Generate pitch using the Ollama HTTP API with JSON format."""
        prompt = _build_prompt(context, preset)
        model = preset.get("model", self.model) if preset else self.model
        url = f"{self.settings.ollama_url}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.3},
        }

        try:
            response = httpx.post(url, json=payload, timeout=120)
            response.raise_for_status()
        except Exception as exc:
            raise ConnectorError(f"Ollama API request failed: {exc}") from exc

        data = response.json()
        raw = data.get("response", "{}").strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ConnectorError(f"Ollama response is not valid JSON: {exc}") from exc

        return PitchResult(
            pitch_text=parsed.get("pitch_text", ""),
            membership_idea=parsed.get("membership_idea", ""),
            website_benefits=parsed.get("website_benefits", ""),
            model_used=parsed.get("model_used", "ollama"),
        )

    def health_check(self) -> bool:
        """Check if the Ollama server is reachable."""
        try:
            response = httpx.get(f"{self.settings.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    @classmethod
    def can_use(cls) -> bool:
        """Check if the Ollama server is reachable without instantiating."""
        try:
            response = httpx.get(f"{get_settings().ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
