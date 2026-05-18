"""OpenRouter API connector (OpenAI-compatible)."""

from __future__ import annotations

import json
import logging
from typing import Any

from src.config import get_settings
from src.connectors.llm.base import BusinessContext, ConnectorError, LLMConnector, PitchResult

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "openai/gpt-4o-mini"
_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant that writes personalized business pitches. "
    "Always respond with valid JSON containing pitch_text, membership_idea, website_benefits, and model_used."
)

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

try:
    from openai import APIError as _OpenAIAPIError
    from openai import APITimeoutError as _OpenAITimeoutError
except ImportError:
    _OpenAIAPIError = type("_OpenAIAPIError", (Exception,), {})
    _OpenAITimeoutError = type("_OpenAITimeoutError", (Exception,), {})


def _build_messages(context: BusinessContext, preset: dict | None = None) -> list[dict[str, str]]:
    """Build OpenRouter chat messages from business context."""
    preset = preset or {}
    issues = ", ".join(context.website_issues) if context.website_issues else "none"
    system_prompt = preset.get("system_prompt", _DEFAULT_SYSTEM_PROMPT)
    tone = preset.get("tone")
    if tone:
        system_prompt = f"{system_prompt} Use a {tone} tone."

    user_prompt = (
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
        "- model_used: set to 'openrouter'\n\n"
        "Return ONLY valid JSON."
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


class OpenRouterConnector(LLMConnector):
    """Connector for OpenRouter API (OpenAI-compatible)."""

    def __init__(self, model: str | None = None) -> None:
        self.settings = get_settings()
        self.model = model or getattr(self.settings, "openrouter_model", _DEFAULT_MODEL)
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-load the OpenAI client pointing at OpenRouter."""
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ConnectorError("openai package is not installed") from exc

        api_key = getattr(self.settings, "openrouter_api_key", "")
        if not api_key:
            raise ConnectorError("OPENROUTER_API_KEY is not configured")

        self._client = OpenAI(
            base_url=_OPENROUTER_BASE_URL,
            api_key=api_key,
        )
        return self._client

    def generate_pitch(self, context: BusinessContext, preset: dict | None = None) -> PitchResult:
        """Generate pitch using the OpenRouter API with JSON mode."""
        client = self._get_client()
        messages = _build_messages(context, preset)
        model = preset.get("model", self.model) if preset else self.model
        timeout = (
            preset.get("timeout", self.settings.llm_timeout_ms / 1000.0)
            if preset
            else self.settings.llm_timeout_ms / 1000.0
        )

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1024,
                timeout=timeout,
            )
        except Exception as exc:
            msg = f"OpenRouter API request failed: {exc}"
            if isinstance(exc, _OpenAITimeoutError):
                msg = "OpenRouter API request timed out"
            raise ConnectorError(msg) from exc

        raw = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ConnectorError(f"OpenRouter response is not valid JSON: {exc}") from exc

        return PitchResult(
            pitch_text=parsed.get("pitch_text", ""),
            membership_idea=parsed.get("membership_idea", ""),
            website_benefits=parsed.get("website_benefits", ""),
            model_used=parsed.get("model_used", "openrouter"),
        )

    def health_check(self) -> bool:
        """Check if the OpenRouter API key is configured and has a valid format."""
        key = getattr(self.settings, "openrouter_api_key", "")
        return bool(key) and key.startswith("sk-")

    @classmethod
    def can_use(cls) -> bool:
        """Check if an OpenRouter API key is present without instantiating a client."""
        return bool(getattr(get_settings(), "openrouter_api_key", ""))
