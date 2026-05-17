"""OpenRouter API connector (stub)."""

from __future__ import annotations

from src.connectors.llm.base import BusinessContext, LLMConnector, PitchResult


class OpenRouterConnector(LLMConnector):
    """Stub connector for OpenRouter — not yet implemented."""

    def generate_pitch(self, context: BusinessContext, preset: dict | None = None) -> PitchResult:
        """Raise NotImplementedError."""
        raise NotImplementedError("OpenRouter connector not yet implemented")

    def health_check(self) -> bool:
        """Always returns False."""
        return False

    @classmethod
    def can_use(cls) -> bool:
        """Always returns False."""
        return False
