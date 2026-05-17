"""Proxy rotation with health tracking."""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)


class ProxyError(Exception):
    """Raised when a proxy-related error occurs."""


class ProxyPool:
    """Manages a pool of HTTP proxies with failure tracking."""

    def __init__(
        self,
        proxies: list[str] | None = None,
        proxy_file: str | None = None,
        max_failures: int = 3,
    ) -> None:
        self.proxies: list[str] = []
        self.max_failures = max_failures
        self.failure_counts: dict[str, int] = {}
        self._index = 0

        if proxies:
            self.proxies = proxies
        elif proxy_file and Path(proxy_file).exists():
            self._load_from_file(proxy_file)

    def _load_from_file(self, path: str) -> None:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    self.proxies.append(line)

    def get_next(self) -> str | None:
        """Return the next available proxy, skipping dead ones."""
        if not self.proxies:
            return None
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self._index % len(self.proxies)]
            self._index += 1
            if self.failure_counts.get(proxy, 0) < self.max_failures:
                return proxy
            attempts += 1
        logger.warning("All proxies have exceeded max_failures")
        return None

    def mark_failed(self, proxy: str) -> None:
        """Increment failure count for a proxy."""
        self.failure_counts[proxy] = self.failure_counts.get(proxy, 0) + 1
        logger.info("Proxy %s failure count: %d", proxy, self.failure_counts[proxy])

    def mark_success(self, proxy: str) -> None:
        """Reset failure count for a proxy on success."""
        if proxy in self.failure_counts:
            del self.failure_counts[proxy]

    def add_proxy(self, proxy: str) -> None:
        """Add a new proxy to the pool."""
        if proxy not in self.proxies:
            self.proxies.append(proxy)

    @classmethod
    def from_free_proxy_list(cls, timeout: int = 10) -> ProxyPool:
        """Scrape free proxies from free-proxy-list.net (best-effort)."""
        try:
            resp = requests.get(
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
                timeout=timeout,
            )
            resp.raise_for_status()
            proxies = [f"http://{line.strip()}" for line in resp.text.splitlines() if line.strip()]
            logger.info("Loaded %d free proxies", len(proxies))
            return cls(proxies=proxies)
        except Exception as exc:
            logger.warning("Failed to load free proxy list: %s", exc)
            return cls()
