"""Rate limiting for polite scraping."""

from __future__ import annotations

import asyncio
import time
from datetime import date


class RateLimitError(Exception):
    """Raised when a rate limit is exceeded."""


class RateLimiter:
    """Enforce delays and daily limits per proxy."""

    def __init__(
        self,
        min_delay: float = 2.0,
        daily_limit: int = 500,
        redis_client=None,
    ) -> None:
        self.min_delay = min_delay
        self.daily_limit = daily_limit
        self._last_request: dict[str, float] = {}
        self._redis = redis_client

    async def wait(self, proxy_id: str) -> None:
        """Async wait until min_delay has elapsed since last request."""
        now = time.time()
        last = self._last_request.get(proxy_id, 0)
        elapsed = now - last
        if elapsed < self.min_delay:
            await asyncio.sleep(self.min_delay - elapsed)
        self._last_request[proxy_id] = time.time()

    def can_use(self, proxy_id: str) -> bool:
        """Check if proxy has not exceeded daily limit."""
        if self._redis:
            today = date.today().isoformat()
            key = f"proxy:{proxy_id}:count:{today}"
            count = int(self._redis.get(key) or 0)
            return count < self.daily_limit
        return True  # Without Redis, always allow

    def record_use(self, proxy_id: str) -> None:
        """Record that a request was made via this proxy."""
        if self._redis:
            today = date.today().isoformat()
            key = f"proxy:{proxy_id}:count:{today}"
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, 86400)
            pipe.execute()
