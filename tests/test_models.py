"""Tests for database models."""

from datetime import datetime, timezone

from src.models import Lead, Outreach, OutreachChannel, OutreachStatus


class TestLeadModel:
    """Test suite for Lead model."""

    def test_create_lead(self) -> None:
        """Lead can be instantiated with required fields."""
        lead = Lead(
            city="Mumbai",
            business_name="Test Cafe",
            business_type="cafe",
            address="123 Main St",
            google_maps_url="https://maps.example.com/1",
        )
        assert lead.city == "Mumbai"
        assert lead.business_name == "Test Cafe"
        assert lead.business_type == "cafe"
        assert lead.address == "123 Main St"
        assert lead.phone is None
        assert lead.email is None
        # Defaults are applied at flush time, not during __init__

    def test_lead_repr(self) -> None:
        """Repr should include id, name and city."""
        lead = Lead(id=1, city="Mumbai", business_name="Test Cafe")
        assert "Test Cafe" in repr(lead)
        assert "Mumbai" in repr(lead)

    def test_lead_outreaches_relationship(self) -> None:
        """Lead should have outreaches list."""
        lead = Lead(city="Mumbai", business_name="Test Cafe")
        assert lead.outreaches == []

    def test_lead_website_audit_field(self) -> None:
        """Lead should accept website_audit dict."""
        audit = {
            "has_website": True,
            "mobile_friendly": False,
            "overall_score": "poor",
            "layout_issues": ["missing_viewport_meta"],
        }
        lead = Lead(
            city="Mumbai",
            business_name="Test Cafe",
            website_audit=audit,
        )
        assert lead.website_audit == audit
        assert lead.website_audit["overall_score"] == "poor"


class TestOutreachModel:
    """Test suite for Outreach model."""

    def test_create_outreach(self) -> None:
        """Outreach can be instantiated with defaults."""
        outreach = Outreach(
            lead_id=1,
            channel=OutreachChannel.EMAIL,
            message_text="Hello",
            context_summary="Initial pitch",
        )
        assert outreach.lead_id == 1
        assert outreach.channel == OutreachChannel.EMAIL
        # status default is applied at flush time
        assert outreach.message_text == "Hello"
        assert outreach.sent_at is None
        # created_at default is applied at flush time

    def test_outreach_status_enum(self) -> None:
        """Status enum values should be strings."""
        assert OutreachStatus.SENT.value == "sent"
        assert OutreachStatus.FAILED.value == "failed"
        assert OutreachStatus.PENDING.value == "pending"
        assert OutreachStatus.RESPONDED.value == "responded"

    def test_outreach_channel_enum(self) -> None:
        """Channel enum values should be strings."""
        assert OutreachChannel.EMAIL.value == "email"
        assert OutreachChannel.WHATSAPP.value == "whatsapp"

    def test_outreach_repr(self) -> None:
        """Repr should include id, lead_id, channel and status."""
        outreach = Outreach(
            id=1,
            lead_id=2,
            channel=OutreachChannel.EMAIL,
            status=OutreachStatus.SENT,
        )
        rep = repr(outreach)
        assert "1" in rep
        assert "2" in rep
        assert "email" in rep
        assert "sent" in rep
