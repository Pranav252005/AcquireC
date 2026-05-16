"""Tests for messenger module."""

from unittest.mock import MagicMock, patch

import pytest

from src.messenger import EmailSender, WhatsAppError, WhatsAppSender


class TestEmailSender:
    """Test suite for EmailSender."""

    def test_send_calls_smtplib(self) -> None:
        """send should call smtplib.SMTP."""
        sender = EmailSender()
        mock_server = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_server)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        with patch("smtplib.SMTP", return_value=mock_ctx):
            sender.send("test@example.com", "Hello", "Body text")
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()


class TestWhatsAppSender:
    """Test suite for WhatsAppSender."""

    def test_init(self) -> None:
        """Should initialize with settings."""
        sender = WhatsAppSender()
        assert sender.headless is False
        assert sender.session_path is not None

    def test_invalid_phone_raises(self) -> None:
        """Invalid phone should raise ValueError."""
        sender = WhatsAppSender()
        with pytest.raises(ValueError):
            sender.send("not-a-number", "Hello")

    def test_whatsapp_error_is_exception(self) -> None:
        """WhatsAppError should be catchable."""
        with pytest.raises(WhatsAppError):
            raise WhatsAppError("test")
