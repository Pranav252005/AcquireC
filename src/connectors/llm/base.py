"""Abstract base class and shared types for LLM connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BusinessContext:
    """Context required for pitch generation."""

    business_type: str
    maturity_stage: str | None
    website_score: str | None
    years_in_business: int | None
    city: str
    name: str
    has_website: bool
    website_issues: list[str]


@dataclass
class PitchResult:
    """Structured result from pitch generation."""

    pitch_text: str
    membership_idea: str
    website_benefits: str
    model_used: str


class ConnectorError(Exception):
    """Raised when an LLM connector encounters an error."""

    pass


class LLMConnector(ABC):
    """Abstract base class for LLM connectors."""

    @abstractmethod
    def generate_pitch(self, context: BusinessContext, preset: dict | None = None) -> PitchResult:
        """Generate a pitch for the given business context.

        Args:
            context: Business context with lead information.
            preset: Optional preset overrides.

        Returns:
            PitchResult with generated pitch and metadata.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the connector is healthy and ready to use.

        Returns:
            True if the connector is available, False otherwise.
        """
        pass

    @classmethod
    def can_use(cls) -> bool:
        """Check whether this connector class can be used without instantiating.

        Defaults to creating an instance and calling health_check(). Subclasses
        should override with a lightweight class-level check when instantiation
        is expensive or unnecessary.

        Returns:
            True if the connector is likely available.
        """
        return cls().health_check()
