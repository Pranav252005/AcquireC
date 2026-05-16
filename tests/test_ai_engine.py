"""Tests for AI engine module."""

from unittest.mock import MagicMock, patch

import pytest

from src.ai_engine import (
    AIPitchEngine,
    BusinessContext,
    PitchCacheManager,
    PitchValidator,
    TemperatureScheduler,
)


class TestTemperatureScheduler:
    def test_get_analysis(self) -> None:
        assert TemperatureScheduler.get("analysis") == 0.1

    def test_get_draft(self) -> None:
        assert TemperatureScheduler.get("draft") == 0.3

    def test_get_unknown_defaults(self) -> None:
        assert TemperatureScheduler.get("unknown") == 0.3


class TestPitchValidator:
    def test_valid_pitch_passes(self) -> None:
        v = PitchValidator()
        result = v.validate({
            "pitch_text": "This is a valid pitch about building a professional website for your business. It has enough words to pass validation and mentions website multiple times to ensure it meets all requirements. We specialize in creating modern, mobile-friendly websites that help local businesses like yours attract more customers and increase revenue significantly.",
            "context_summary": "Cafe pitch for Mumbai",
            "membership_idea": "Regulars Club with monthly subscription and free coffee daily for all loyal customers.",
            "website_benefits": "Online menu with photos, table booking system, and customer review aggregation.",
        })
        assert result == []

    def test_short_pitch_fails(self) -> None:
        v = PitchValidator()
        result = v.validate({
            "pitch_text": "Too short",
            "context_summary": "OK",
            "membership_idea": "OK",
            "website_benefits": "OK",
        })
        assert any("too short" in e for e in result)

    def test_missing_website_keyword_fails(self) -> None:
        v = PitchValidator()
        result = v.validate({
            "pitch_text": "This is a long pitch about digital marketing and social media growth for your business. It does not mention web pages or domains at all.",
            "context_summary": "OK",
            "membership_idea": "OK",
            "website_benefits": "OK",
        })
        assert any("missing" in e.lower() for e in result)


class TestPitchCacheManager:
    def test_hash_context_is_deterministic(self) -> None:
        ctx = BusinessContext(
            name="Test",
            city="Mumbai",
            business_type="cafe",
            years_in_business=5,
            has_website=False,
            website_score="none",
            website_issues=[],
            linkedin_summary="",
            offerings="",
        )
        h1 = PitchCacheManager._hash_context(ctx)
        h2 = PitchCacheManager._hash_context(ctx)
        assert h1 == h2
        assert len(h1) == 64  # SHA256 hex

    def test_different_contexts_different_hashes(self) -> None:
        ctx1 = BusinessContext(
            name="Test", city="Mumbai", business_type="cafe",
            years_in_business=5, has_website=False, website_score="none",
            website_issues=[], linkedin_summary="", offerings="",
        )
        ctx2 = BusinessContext(
            name="Test", city="Mumbai", business_type="salon",
            years_in_business=5, has_website=False, website_score="none",
            website_issues=[], linkedin_summary="", offerings="",
        )
        assert PitchCacheManager._hash_context(ctx1) != PitchCacheManager._hash_context(ctx2)


class TestAIPitchEngine:
    def test_template_fallback_returns_structured_output(self) -> None:
        engine = AIPitchEngine()
        ctx = BusinessContext(
            name="Cafe Largo",
            city="Mumbai",
            business_type="cafe",
            years_in_business=8,
            has_website=False,
            website_score="none",
            website_issues=[],
            linkedin_summary="",
            offerings="",
        )
        result = engine._template_fallback(ctx)
        assert "pitch_text" in result
        assert "membership_idea" in result
        assert "website_benefits" in result
        assert "Cafe Largo" in result["pitch_text"]
        assert "Mumbai" in result["pitch_text"]
