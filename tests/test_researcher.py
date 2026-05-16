"""Tests for researcher module."""

from unittest.mock import MagicMock, patch

import pytest

from src.models import Lead
from src.researcher import LinkedInResearcher


class TestLinkedInResearcher:
    """Test suite for LinkedInResearcher."""

    def test_init(self) -> None:
        """Should initialize with settings."""
        r = LinkedInResearcher()
        assert r.headless is True
        assert r.settings is not None

    def test_research_returns_dict(self) -> None:
        """research should return a dict with expected keys."""
        r = LinkedInResearcher()
        lead = Lead(
            id=1,
            city="Mumbai",
            business_name="Test Cafe",
            business_type="cafe",
            address="A street",
            google_maps_url="https://maps.example.com/1",
        )
        db = MagicMock()
        with patch.object(r, "_scrape_linkedin", return_value={
            "url": "https://linkedin.com/company/test",
            "summary": "Great coffee",
            "years": 5,
            "offerings": "Espresso, pastries",
        }):
            with patch.object(r.ai_engine, "generate", return_value={
                "pitch_text": "Hello from pitch",
                "context_summary": "Cafe context",
                "membership_idea": "Regulars Club",
                "website_benefits": "Online menu",
            }):
                result = r.research(db, lead)
        assert "pitch_text" in result
        assert "context_summary" in result
        assert "membership_idea" in result
        assert "website_benefits" in result
        assert "maturity_stage" in result
        assert "lead_score" in result
        assert result["pitch_text"] == "Hello from pitch"

    def test_fallback_pitch(self) -> None:
        """Fallback pitch should include business name and city."""
        lead = Lead(
            city="Delhi",
            business_name="Alpha Clinic",
            business_type="clinic",
            address="D road",
            google_maps_url="https://maps.example.com/4",
        )
        pitch = LinkedInResearcher._fallback_pitch(lead)
        assert "Alpha Clinic" in pitch
        assert "Delhi" in pitch

    def test_fallback_pitch_with_audit(self) -> None:
        """Fallback pitch should reference audit issues."""
        lead = Lead(
            city="Delhi",
            business_name="Beta Shop",
            business_type="retail",
            address="E road",
            google_maps_url="https://maps.example.com/5",
        )
        audit = {
            "overall_score": "poor",
            "layout_issues": ["missing_viewport_meta", "bloated_dom_4000_nodes"],
            "old_tech_detected": ["deprecated_tag_font"],
            "load_time_ms": 6200,
        }
        pitch = LinkedInResearcher._fallback_pitch(lead, website_audit=audit)
        assert "Beta Shop" in pitch
        assert "missing_viewport_meta" in pitch
