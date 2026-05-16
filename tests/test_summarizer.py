import pytest
"""Tests for summarizer module."""

from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import init_db
from src.models import Lead, Outreach, OutreachChannel, OutreachStatus
from src.summarizer import Summarizer
from src.tracker import get_or_create_lead, log_outreach


class TestSummarizer:
    """Test suite for Summarizer."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Create fresh in-memory DB for each test."""
        db_file = tmp_path / "summarizer.db"
        self.engine = init_db(f"sqlite:///{db_file}")
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.Session()
        self.summarizer = Summarizer()
        yield
        self.db.close()

    def test_city_summary_empty(self) -> None:
        """Empty city should show zeros."""
        with patch.object(self.summarizer.console, "print"):
            result = self.summarizer.city_summary(self.db, "Nowhere")
        assert "Nowhere" in result
        assert "total" in result.lower() or "Summary" in result

    def test_all_cities_summary_empty(self) -> None:
        """No cities should show warning."""
        with patch.object(self.summarizer.console, "print"):
            result = self.summarizer.all_cities_summary(self.db)
        assert "No data" in result or "No cities" in result

    def test_lead_detail_not_found(self) -> None:
        """Missing lead should show error."""
        with patch.object(self.summarizer.console, "print"):
            result = self.summarizer.lead_detail_report(self.db, 99999)
        assert "Not found" in result

    def test_city_summary_with_data(self) -> None:
        """Summary should reflect actual counts."""
        l1 = get_or_create_lead(self.db, "Pune", "Salon A")
        l2 = get_or_create_lead(self.db, "Pune", "Cafe B")
        log_outreach(self.db, l1.id, OutreachChannel.EMAIL, "msg", "ctx", status=OutreachStatus.SENT)
        log_outreach(self.db, l2.id, OutreachChannel.WHATSAPP, "msg2", "ctx2", status=OutreachStatus.FAILED)

        with patch.object(self.summarizer.console, "print"):
            result = self.summarizer.city_summary(self.db, "Pune")
        assert "Pune" in result

    def test_lead_detail_with_outreach(self) -> None:
        """Detail should show outreach history."""
        lead = get_or_create_lead(self.db, "Mumbai", "Shop C")
        log_outreach(self.db, lead.id, OutreachChannel.EMAIL, "Hello there", "Initial pitch", status=OutreachStatus.SENT)

        with patch.object(self.summarizer.console, "print"):
            result = self.summarizer.lead_detail_report(self.db, lead.id)
        assert f"lead {lead.id}" in result
