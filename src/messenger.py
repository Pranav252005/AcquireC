"""Email + WhatsApp messaging module."""

import logging
import re
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from playwright.sync_api import sync_playwright

from src.config import get_settings
from src.vision_agent import VisionAgent

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
    """Send WhatsApp messages via WhatsApp Web using Playwright."""

    def __init__(self, headless: bool | None = None) -> None:
        self.settings = get_settings()
        self.headless = headless if headless is not None else not self.settings.vision_headed
        self.session_path = self.settings.whatsapp_session_path
        self._playwright = None
        self._context = None
        self._page = None

    def _ensure_context(self):
        """Return a reusable persistent browser context, creating one if needed."""
        if self._context is not None:
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
            # Wait for either QR code scan or chat list (authenticated)
            try:
                # If chat list appears, we're already logged in
                page.wait_for_selector('div[aria-label="Chat list"]', timeout=30000)
                return True
            except Exception:
                # Wait longer for QR scan
                try:
                    page.wait_for_selector('div[aria-label="Chat list"]', timeout=120000)
                    return True
                except Exception:
                    return False
        finally:
            page.close()

    def send(self, phone: str, message: str) -> None:
        """Send a WhatsApp message to a phone number."""
        cleaned = re.sub(r"[^\d]", "", phone)
        if not cleaned:
            raise ValueError(f"Invalid phone number: {phone}")

        context = self._ensure_context()
        page = context.new_page()

        try:
            logger.info("Navigating to WhatsApp Web for phone: %s", cleaned)
            page.goto(
                f"https://web.whatsapp.com/send?phone={cleaned}",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            # Wait for chat to load or "phone number not on WhatsApp" message
            page.wait_for_timeout(5000)

            # Check if number is not on WhatsApp
            logger.info("Checking if phone number is valid on WhatsApp")
            invalid = page.locator('div:has-text("Phone number shared via url is invalid")')
            if invalid.count() > 0 and invalid.first.is_visible(timeout=3000):
                raise WhatsAppError(f"Phone number {phone} is not on WhatsApp")

            # Wait for chat input
            logger.info("Waiting for chat input box")
            try:
                input_box = page.locator('div[contenteditable="true"][data-tab="1"]')
                input_box.wait_for(timeout=30000)
                logger.info("Chat input box found")
            except Exception:
                logger.warning("Primary chat input selector failed, trying vision fallback")
                # Vision fallback: ask VLM to find the message input area
                agent = VisionAgent(page, max_steps=3)
                agent.run_task("Find the WhatsApp message text input field and click it so I can type")
                # After vision agent runs, try again or proceed
                try:
                    input_box = page.locator('div[contenteditable="true"]')
                    input_box.wait_for(timeout=10000)
                    logger.info("Chat input found via vision fallback")
                except Exception as exc:
                    raise WhatsAppError(f"Could not locate WhatsApp chat input: {exc}")

            # Type message (click first, then type with delay for contenteditable)
            logger.info("Typing message")
            try:
                input_box.click()
                input_box.type(message, delay=50)
            except Exception:
                logger.warning("Direct typing failed, trying vision fallback")
                # Vision fallback for typing
                agent = VisionAgent(page, max_steps=2)
                agent.run_task(f"Type this exact message into the WhatsApp chat input: {message}")
            page.wait_for_timeout(500)

            # Press Enter to send
            logger.info("Sending message")
            try:
                input_box.press("Enter")
            except Exception:
                logger.warning("Pressing Enter failed, trying vision fallback")
                # Vision fallback: ask VLM to press the send button
                agent = VisionAgent(page, max_steps=2)
                agent.run_task("Click the send button in WhatsApp to send the message")
            page.wait_for_timeout(3000)
            logger.info("Message sent successfully")

            # Rate limiting
            time.sleep(3)
        finally:
            page.close()

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
