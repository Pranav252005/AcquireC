"""Tests for follow-up module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.follow_up import DEFAULT_SEQUENCE, FollowUpEngine
from src.models import OutreachChannel, OutreachStatus


class TestFollowUpEngine:
    def test_default_sequence_has_days(self) -> None:
        assert len(DEFAULT_SEQUENCE) > 0
        for step in DEFAULT_SEQUENCE:
            assert "day" in step
            assert "channel" in step
            assert "template" in step

    def test_schedule_for_lead_creates_records(self) -> None:
        engine = FollowUpEngine()
        db = MagicMock()
        lead = MagicMock()
        lead.id = 1

        records = engine.schedule_for_lead(db, lead, "test pitch", "test context")

        assert len(records) == len(DEFAULT_SEQUENCE)
        db.commit.assert_called_once()

    def test_get_pending_follow_ups_queries_correctly(self) -> None:
        engine = FollowUpEngine()
        db = MagicMock()
        mock_query = MagicMock()
        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        result = engine.get_pending_follow_ups(db)
        assert result == []

    def test_cancel_sequence_updates_status(self) -> None:
        engine = FollowUpEngine()
        db = MagicMock()
        mock_query = MagicMock()
        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.update.return_value = 2

        count = engine.cancel_sequence(db, 1)
        assert count == 2
        db.commit.assert_called_once()
