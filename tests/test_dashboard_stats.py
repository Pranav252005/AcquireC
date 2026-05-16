"""Tests for dashboard SQL-optimized stats."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import init_db
from src.models import Base, Lead, Outreach, OutreachChannel, OutreachStatus
from src.tracker import get_outreach_stats, get_or_create_lead, log_outreach


class TestGetOutreachStats:
    """Test suite for get_outreach_stats SQL aggregation."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        db_file = tmp_path / "stats.db"
        self.engine = init_db(f"sqlite:///{db_file}")
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.Session()
        yield
        self.db.close()

    def test_empty_db_returns_zeros(self) -> None:
        """No outreaches should return all zeros."""
        stats = get_outreach_stats(self.db)
        assert stats == {"contacted": 0, "failed": 0, "responded": 0, "pending": 0}

    def test_counts_by_status(self) -> None:
        """Should correctly count outreaches by status."""
        lead1 = get_or_create_lead(self.db, "Pune", "Shop A")
        lead2 = get_or_create_lead(self.db, "Pune", "Shop B")
        lead3 = get_or_create_lead(self.db, "Pune", "Shop C")

        log_outreach(self.db, lead1.id, OutreachChannel.EMAIL, "msg1", "ctx1", status=OutreachStatus.SENT)
        log_outreach(self.db, lead2.id, OutreachChannel.EMAIL, "msg2", "ctx2", status=OutreachStatus.FAILED)
        log_outreach(self.db, lead3.id, OutreachChannel.WHATSAPP, "msg3", "ctx3", status=OutreachStatus.RESPONDED)

        stats = get_outreach_stats(self.db)
        assert stats["contacted"] == 1
        assert stats["failed"] == 1
        assert stats["responded"] == 1
        assert stats["pending"] == 0

    def test_multiple_same_status(self) -> None:
        """Multiple outreaches with same status should aggregate."""
        for i in range(3):
            lead = get_or_create_lead(self.db, "Mumbai", f"Biz {i}")
            log_outreach(self.db, lead.id, OutreachChannel.EMAIL, f"msg{i}", "ctx", status=OutreachStatus.SENT)

        stats = get_outreach_stats(self.db)
        assert stats["contacted"] == 3
        assert stats["failed"] == 0
        assert stats["responded"] == 0
        assert stats["pending"] == 0

    def test_mixed_statuses(self) -> None:
        """A mix of all statuses should be counted correctly."""
        statuses = [
            OutreachStatus.SENT,
            OutreachStatus.FAILED,
            OutreachStatus.PENDING,
            OutreachStatus.RESPONDED,
            OutreachStatus.SENT,
        ]
        for i, status in enumerate(statuses):
            lead = get_or_create_lead(self.db, "Delhi", f"Biz {i}")
            log_outreach(self.db, lead.id, OutreachChannel.EMAIL, f"msg{i}", "ctx", status=status)

        stats = get_outreach_stats(self.db)
        assert stats["contacted"] == 2
        assert stats["failed"] == 1
        assert stats["responded"] == 1
        assert stats["pending"] == 1
