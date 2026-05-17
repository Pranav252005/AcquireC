"""Tests for Celery tasks and configuration."""

import pytest

from src.celery_app import celery_app
from src.tasks import discover_city_task, enrich_lead_task


class TestCeleryTasks:
    """Test suite for Celery task definitions."""

    def test_discover_city_task_returns_expected_dict(self) -> None:
        """discover_city_task should return metadata dict."""
        result = discover_city_task.run(city="Mumbai", category="salon", max_leads=10)
        assert result == {
            "city": "Mumbai",
            "category": "salon",
            "max_leads": 10,
            "status": "queued",
        }

    def test_enrich_lead_task_returns_expected_dict(self) -> None:
        """enrich_lead_task should return metadata dict."""
        result = enrich_lead_task.run(lead_id=42)
        assert result == {"lead_id": 42, "status": "queued"}

    def test_celery_app_configured_with_correct_broker_backend(self, monkeypatch) -> None:
        """celery_app should derive broker and backend from settings."""
        from src import config

        class FakeSettings:
            redis_url = "redis://test-redis:6379/1"
            celery_broker_url = ""
            celery_result_backend = ""

        monkeypatch.setattr(config, "get_settings", lambda: FakeSettings())

        # Re-import to pick up patched settings
        from importlib import reload
        import src.celery_app as celery_module

        reloaded = reload(celery_module)
        assert reloaded.celery_app.conf.broker_url == "redis://test-redis:6379/1"
        assert reloaded.celery_app.conf.result_backend == "redis://test-redis:6379/1"
