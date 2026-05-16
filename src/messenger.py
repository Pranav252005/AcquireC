"""Email + WhatsApp messaging module."""

import logging
import re
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from playwright.sync_api import Browser, sync_playwright

from src.config import get_settings

logger = logging.getLogger(__name__)


class EmailSender:
    """Send emails via SMTP."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def send(self, to: str, subject: str, body: str) -> None:
        """Send an email."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.settings.smtp_from or self.settings.smtp_user
        msg["To"] = to
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=30) as server:
            server.starttls()
            server.login(self.settings.smtp_user, self.settings.smtp_password)
            server.sendmail(msg["From"], [to], msg.as_string())


class WhatsAppSender:
    """WhatsApp Web automation for drafting messages.

    WARNING: Automated sending violates Meta's Terms of Service and will
    result in a permanent ban. This class is kept for manual auth
    verification and draft creation only. Do NOT use send() for bulk
    outreach.
    """

    def __init__(self, headless: bool | None = None, browser: Browser | None = None) -> None:
        self.settings = get_settings()
        self.headless = headless if headless is not None else not self.settings.vision_headed
        self.session_path = self.settings.whatsapp_session_path
        self.browser = browser
        self._playwright = None
        self._context = None
        self._page = None

    def _ensure_context(self):
        """Return a reusable persistent browser context, creating one if needed."""
        if self._context is not None:
            return self._context
        if self.browser is not None:
            # Cannot use persistent context with external browser; use regular context
            self._context = self.browser.new_context()
            return self._context
        if self._playwright is None:
            self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.session_path),
            headless=self.headless,
            viewport={"width": 1280, "height": 800},
        )
        return self._context

    def ensure_auth(self) -> bool:
        """Open WhatsApp Web and wait for QR scan or existing session."""
        context = self._ensure_context()
        page = context.new_page()
        try:
            page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_selector('div[aria-label="Chat list"]', timeout=30000)
                return True
            except Exception:
                try:
                    page.wait_for_selector('div[aria-label="Chat list"]', timeout=120000)
                    return True
                except Exception:
                    return False
        finally:
            page.close()

    def create_draft(self, phone: str, message: str) -> dict[str, str]:
        """Return a draft dict for manual sending. Does NOT send automatically."""
        cleaned = re.sub(r"[^\d]", "", phone)
        if not cleaned:
            raise ValueError(f"Invalid phone number: {phone}")
        return {
            "phone": cleaned,
            "message": message,
            "link": f"https://wa.me/{cleaned}?text={requests_utils_quote(message)}",
        }

    def send(self, phone: str, message: str) -> None:
        """DEPRECATED: Automated WhatsApp sending is disabled.

        Use create_draft() for manual copy-paste sending instead.
        """
        raise WhatsAppError(
            "Automated WhatsApp sending is disabled to prevent account bans. "
            "Use create_draft() to generate a manual message link."
        )

    def close(self) -> None:
        """Close the browser context and playwright instance."""
        if self._context:
            self._context.close()
            self._context = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None


class WhatsAppError(Exception):
    """Raised when WhatsApp sending fails."""


def requests_utils_quote(s: str) -> str:
    """Lightweight URL quoting for WhatsApp message links."""
    # Basic quoting for common chars; not full urllib.parse.quote
    repl = {
        " ": "%20",
        "\n": "%0A",
        "&": "%26",
        "?": "%3F",
        "=": "%3D",
        "#": "%23",
        "%": "%25",
    }
    for old, new in repl.items():
        s = s.replace(old, new)
    return s
