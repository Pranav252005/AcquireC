"""Shared Playwright browser pool to avoid launching multiple browsers."""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Browser, BrowserContext, Playwright, sync_playwright

from src.config import get_settings


class BrowserPool:
    """Manage a single Playwright browser instance with optional proxy."""

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    def _proxy_kwargs(self) -> dict[str, Any] | None:
        settings = get_settings()
        if not settings.proxy_server:
            return None
        proxy: dict[str, Any] = {"server": settings.proxy_server}
        if settings.proxy_username:
            proxy["username"] = settings.proxy_username
        if settings.proxy_password:
            proxy["password"] = settings.proxy_password
        return proxy

    def get_browser(self) -> Browser:
        if self._browser is None:
            self._playwright = sync_playwright().start()
            kwargs: dict[str, Any] = {"headless": self.headless}
            proxy = self._proxy_kwargs()
            if proxy:
                kwargs["proxy"] = proxy
            self._browser = self._playwright.chromium.launch(**kwargs)
        return self._browser

    def new_context(
        self,
        viewport: dict[str, int] | None = None,
        user_agent: str | None = None,
    ) -> BrowserContext:
        browser = self.get_browser()
        kwargs: dict[str, Any] = {}
        if viewport:
            kwargs["viewport"] = viewport
        if user_agent:
            kwargs["user_agent"] = user_agent
        proxy = self._proxy_kwargs()
        if proxy:
            kwargs["proxy"] = proxy
        return browser.new_context(**kwargs)

    def close(self) -> None:
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
