"""Tests for rate_limiter module."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.core.rate_limiter import RateLimitError, RateLimiter


class TestRateLimiter:
    """Test suite for RateLimiter."""

    def test_wait_enforces_delay(self) -> None:
        """wait should enforce min_delay between requests."""
        import threading

        limiter = RateLimiter(min_delay=2.0)
        results = []

        def run_wait():
            try:
                asyncio.run(limiter.wait("proxy_1"))
                results.append("ok")
            except Exception as exc:
                results.append(exc)

        with patch("asyncio.sleep") as mock_sleep:
            t = threading.Thread(target=run_wait)
            t.start()
            t.join()
            assert results[-1] == "ok", results[-1]
            mock_sleep.assert_not_called()

            t = threading.Thread(target=run_wait)
            t.start()
            t.join()
            assert results[-1] == "ok", results[-1]
            mock_sleep.assert_called_once()
            assert mock_sleep.call_args[0][0] > 0

    def test_can_use_returns_true_when_under_limit(self) -> None:
        """can_use should return True when proxy is under daily limit."""
        limiter = RateLimiter(daily_limit=500)
        assert limiter.can_use("proxy_1") is True

    def test_can_use_returns_false_when_over_limit(self) -> None:
        """can_use should return False when proxy exceeds daily limit (mock Redis)."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = "501"
        limiter = RateLimiter(daily_limit=500, redis_client=mock_redis)
        assert limiter.can_use("proxy_1") is False

    def test_can_use_returns_true_at_exact_limit(self) -> None:
        """can_use should return True when proxy is exactly at daily limit minus one."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = "499"
        limiter = RateLimiter(daily_limit=500, redis_client=mock_redis)
        assert limiter.can_use("proxy_1") is True

    def test_record_use_increments_redis(self) -> None:
        """record_use should increment Redis counter and set expiry."""
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe
        limiter = RateLimiter(redis_client=mock_redis)
        limiter.record_use("proxy_1")
        mock_pipe.incr.assert_called_once()
        mock_pipe.expire.assert_called_once_with(mock_pipe.incr.call_args[0][0], 86400)
        mock_pipe.execute.assert_called_once()

    def test_rate_limit_error_exists(self) -> None:
        """RateLimitError should be a subclass of Exception."""
        assert issubclass(RateLimitError, Exception)
