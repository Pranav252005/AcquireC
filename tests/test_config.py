"""Tests for configuration module."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.config import Settings, get_settings


class TestSettings:
    """Test suite for Settings model."""

    def test_default_values(self) -> None:
        """Settings should have sensible defaults."""
        with patch.dict(os.environ, {}, clear=True):
            s = Settings()
        assert s.smtp_host == "smtp.gmail.com"
        assert s.smtp_port == 587
        assert s.db_path == "./data/leads.db"
        assert s.dashboard_port == 8080
        assert s.use_vision is True

    def test_env_override(self) -> None:
        """Environment variables should override defaults."""
        env = {
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "465",
            "DB_PATH": "./test.db",
            "USE_VISION": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            s = Settings()
        assert s.smtp_host == "smtp.example.com"
        assert s.smtp_port == 465
        assert s.db_path == "./test.db"
        assert s.use_vision is False

    def test_db_uri_property(self, tmp_path) -> None:
        """db_uri should resolve to absolute sqlite path."""
        s = Settings(db_path=str(tmp_path / "leads.db"))
        assert s.db_uri.startswith("sqlite:///")
        assert "leads.db" in s.db_uri

    def test_whatsapp_session_path(self, tmp_path) -> None:
        """whatsapp_session_path should create directory."""
        session_dir = tmp_path / "wa_session"
        s = Settings(whatsapp_user_data_dir=str(session_dir))
        path = s.whatsapp_session_path
        assert path.exists()
        assert path.is_dir()


class TestGetSettings:
    """Test get_settings factory."""

    def test_returns_settings_instance(self) -> None:
        """get_settings should return a Settings instance."""
        s = get_settings()
        assert isinstance(s, Settings)
