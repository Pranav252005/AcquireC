"""Local LLM connector using llama-cpp-python."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.connectors.llm.base import BusinessContext, ConnectorError, LLMConnector, PitchResult

logger = logging.getLogger(__name__)

# GBNF grammar for guaranteed valid JSON output
PITCH_GRAMMAR = r'''
root ::= "{" ws "\"pitch_text\"" ":" ws string "," ws "\"membership_idea\"" ":" ws string "," ws "\"website_benefits\"" ":" ws string "," ws "\"model_used\"" ":" ws string "}"
ws ::= [ \t\n]*
string ::= "\"" ([^"\\] | "\\" ["\\/bfnrt] | "\\u" [0-9a-fA-F]{4})* "\""
'''

_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant that writes personalized business pitches. "
    "Always respond with valid JSON containing pitch_text, membership_idea, website_benefits, and model_used."
)

_CHAT_TEMPLATES: dict[str, str] = {
    "qwen": (
        "<|im_start|>system\n{system_prompt}<|im_end|>\n"
        "<|im_start|>user\n{user_prompt}<|im_end|>\n"
        "<|im_start|>assistant\n"
    ),
    "chatml": (
        "<|im_start|>system\n{system_prompt}<|im_end|>\n"
        "<|im_start|>user\n{user_prompt}<|im_end|>\n"
        "<|im_start|>assistant\n"
    ),
    "llama": (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        "{system_prompt}<|eot_id|>"
        "<|start_header_id|>user<|end_header_id|>\n\n"
        "{user_prompt}<|eot_id|>"
        "<|start_header_id|>assistant<|end_header_id|>\n\n"
    ),
    "generic": (
        "System: {system_prompt}\n\n"
        "User: {user_prompt}\n\n"
        "Assistant: "
    ),
}


def _build_prompt(context: BusinessContext, preset: dict | None = None) -> str:
    """Build a chat-style prompt for local model inference."""
    preset = preset or {}
    issues = ", ".join(context.website_issues) if context.website_issues else "none"
    tone = preset.get("tone")
    tone_instruction = f" Use a {tone} tone." if tone else ""
    lines = [
        f"Business: {context.name} in {context.city}",
        f"Type: {context.business_type}",
        f"Years in business: {context.years_in_business or 'unknown'}",
        f"Has website: {context.has_website}",
        f"Website score: {context.website_score or 'none'}",
        f"Website issues: {issues}",
        f"Maturity stage: {context.maturity_stage or 'unknown'}",
        "",
        "Generate a personalized business pitch as JSON with these exact keys:",
        "- pitch_text: the outreach message",
        "- membership_idea: a recurring revenue idea for this business",
        "- website_benefits: bullet points on how a new website helps",
        "- model_used: set to 'local'",
        "",
        f"Return ONLY valid JSON.{tone_instruction}",
    ]
    return "\n".join(lines)


def _parse_response(raw: str) -> PitchResult:
    """Parse raw text into a PitchResult, extracting JSON if embedded."""
    raw = raw.strip()
    # Try to find JSON block
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConnectorError(f"Failed to parse local model output as JSON: {exc}") from exc

    return PitchResult(
        pitch_text=parsed.get("pitch_text", ""),
        membership_idea=parsed.get("membership_idea", ""),
        website_benefits=parsed.get("website_benefits", ""),
        model_used=parsed.get("model_used", "local"),
    )


class LocalConnector(LLMConnector):
    """Connector for local llama-cpp-python models."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._model: Any = None

    def _detect_chat_format(self) -> str:
        """Detect chat template from model filename or settings."""
        path_str = str(self.settings.local_model_path).lower()
        if "qwen" in path_str:
            return "qwen"
        if "llama" in path_str or "meta" in path_str:
            return "llama"
        config_format = self.settings.llm_chat_format
        if config_format in _CHAT_TEMPLATES:
            return config_format
        return "generic"

    def _load_model(self) -> Any:
        """Lazy-load the local Llama model."""
        if self._model is not None:
            return self._model

        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise ConnectorError("llama-cpp-python is not installed") from exc

        path = Path(self.settings.local_model_path)
        if not path.exists():
            raise ConnectorError(f"Local model not found: {path}")

        try:
            self._model = Llama(
                model_path=str(path),
                n_ctx=4096,
                verbose=False,
            )
            return self._model
        except Exception as exc:
            raise ConnectorError(f"Failed to load local model: {exc}") from exc

    def generate_pitch(self, context: BusinessContext, preset: dict | None = None) -> PitchResult:
        """Generate pitch using the local llama-cpp-python model.

        Uses GBNF grammar for structured JSON output when available,
        otherwise falls back to plain text and best-effort parsing.
        """
        llm = self._load_model()
        user_prompt = _build_prompt(context, preset)
        preset = preset or {}
        system_prompt = preset.get("system_prompt", _DEFAULT_SYSTEM_PROMPT)

        fmt = self._detect_chat_format()
        template = _CHAT_TEMPLATES.get(fmt, _CHAT_TEMPLATES["generic"])
        full_prompt = template.format(system_prompt=system_prompt, user_prompt=user_prompt)

        kwargs: dict[str, Any] = {
            "max_tokens": 1024,
            "temperature": 0.3,
        }

        if fmt in ("qwen", "chatml"):
            kwargs["stop"] = ["<|im_start|>"]
        elif fmt == "llama":
            kwargs["stop"] = ["<|eot_id|>"]

        # Attempt grammar-constrained generation if the underlying library supports it
        try:
            kwargs["grammar"] = PITCH_GRAMMAR
            output = llm(full_prompt, **kwargs)
        except Exception:
            logger.debug("Grammar-constrained generation failed, falling back to plain text")
            kwargs.pop("grammar", None)
            output = llm(full_prompt, **kwargs)

        raw = output.get("choices", [{}])[0].get("text", "").strip()
        return _parse_response(raw)

    def health_check(self) -> bool:
        """Verify the local model file exists."""
        return Path(self.settings.local_model_path).exists()

    @classmethod
    def can_use(cls) -> bool:
        """Check if the local model file exists without loading it."""
        return Path(get_settings().local_model_path).exists()
