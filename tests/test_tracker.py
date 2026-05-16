"""Tests for tracker module."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import init_db
from src.models import Lead, Outreach, OutreachChannel, OutreachStatus
from src.tracker import (
    get_all_cities,
    get_city_summary,
    get_lead_detail,
    get_or_create_lead,
    has_any_outreach,
    is_already_contacted,
    log_outreach,
)


@pytest.fixture
def db_session(tmp_path):
    """Provide an in-memory DB session for tests."""
    db_file = tmp_path / "tracker_test.db"
    engine = init_db(f"sqlite:///{db_file}")
    Session = sessionmaker(bind=engine)
    with Session() as session:
        yield session


class TestGetOrCreateLead:
    """Test suite for get_or_create_lead."""

    def test_creates_new_lead(self, db_session) -> None:
        """Should create a new lead when none exists."""
        lead = get_or_create_lead(db_session, "Mumbai", "Cafe A")
        assert lead.id is not None
        assert lead.city == "Mumbai"
        assert lead.business_name == "Cafe A"

    def test_returns_existing_lead(self, db_session) -> None:
        """Should return existing lead without duplicate."""
        lead1 = get_or_create_lead(db_session, "Mumbai", "Cafe A")
        lead2 = get_or_create_lead(db_session, "Mumbai", "Cafe A")
        assert lead1.id == lead2.id

    def test_updates_defaults_for_existing(self, db_session) -> None:
        """Should fill missing fields on existing lead."""
        lead = get_or_create_lead(db_session, "Mumbai", "Cafe A")
        assert lead.phone is None
        lead2 = get_or_create_lead(
            db_session, "Mumbai", "Cafe A", defaults={"phone": "+911234567890"}
        )
        assert lead2.id == lead.id
        assert lead2.phone == "+911234567890"


class TestIsAlreadyContacted:
    """Test suite for is_already_contacted."""

    def test_new_lead_returns_false(self, db_session) -> None:
        """No outreach yet — should return False."""
        assert is_already_contacted(db_session, "Mumbai", "New Cafe") is False

    def test_after_sent_outreach_returns_true(self, db_session) -> None:
        """After logging a SENT outreach, should return True."""
        lead = get_or_create_lead(db_session, "Mumbai", "Cafe B")
        log_outreach(
            db_session,
            lead.id,
            OutreachChannel.EMAIL,
            "Hello",
            "Pitch",
            status=OutreachStatus.SENT,
        )
        assert is_already_contacted(db_session, "Mumbai", "Cafe B") is True

    def test_failed_outreach_returns_false(self, db_session) -> None:
        """Failed outreach should not count as contacted."""
        lead = get_or_create_lead(db_session, "Mumbai", "Cafe C")
        log_outreach(
            db_session,
            lead.id,
            OutreachChannel.EMAIL,
            "Hello",
            "Pitch",
            status=OutreachStatus.FAILED,
        )
        assert is_already_contacted(db_session, "Mumbai", "Cafe C") is False


class TestHasAnyOutreach:
    """Test suite for has_any_outreach."""

    def test_no_outreach(self, db_session) -> None:
        assert has_any_outreach(db_session, "Mumbai", "Cafe D") is False

    def test_with_outreach(self, db_session) -> None:
        lead = get_or_create_lead(db_session, "Mumbai", "Cafe E")
        log_outreach(db_session, lead.id, OutreachChannel.WHATSAPP, "Hi", "Test")
        assert has_any_outreach(db_session, "Mumbai", "Cafe E") is True


class TestCitySummary:
    """Test suite for city summary functions."""

    def test_empty_city(self, db_session) -> None:
        """Empty city should return zero counts."""
        summary = get_city_summary(db_session, "Delhi")
        assert summary == {
            "total": 0,
            "contacted": 0,
            "pending": 0,
            "failed": 0,
            "responded": 0,
        }

    def test_counts_are_accurate(self, db_session) -> None:
        """Summary should reflect actual data."""
        l1 = get_or_create_lead(db_session, "Pune", "Salon X")
        l2 = get_or_create_lead(db_session, "Pune", "Cafe Y")
        log_outreach(db_session, l1.id, OutreachChannel.EMAIL, "m1", "c1", status=OutreachStatus.SENT)
        log_outreach(db_session, l2.id, OutreachChannel.WHATSAPP, "m2", "c2", status=OutreachStatus.FAILED)
        summary = get_city_summary(db_session, "Pune")
        assert summary["total"] == 2
        assert summary["contacted"] == 1
        assert summary["failed"] == 1

    def test_all_cities(self, db_session) -> None:
        """Should list all cities with counts."""
        get_or_create_lead(db_session, "A", "Biz1")
        get_or_create_lead(db_session, "B", "Biz2")
        cities = get_all_cities(db_session)
        assert len(cities) == 2
        city_names = {c["city"] for c in cities}
        assert city_names == {"A", "B"}


class TestGetLeadDetail:
    """Test suite for get_lead_detail."""

    def test_returns_lead_with_outreaches(self, db_session) -> None:
        """Should return lead and load outreaches."""
        lead = get_or_create_lead(db_session, "Mumbai", "Cafe Z")
        log_outreach(db_session, lead.id, OutreachChannel.EMAIL, "msg", "ctx")
        result = get_lead_detail(db_session, lead.id)
        assert result is not None
        assert result.business_name == "Cafe Z"
        assert len(result.outreaches) == 1

    def test_missing_lead_returns_none(self, db_session) -> None:
        """Non-existent ID should return None."""
        assert get_lead_detail(db_session, 99999) is None
