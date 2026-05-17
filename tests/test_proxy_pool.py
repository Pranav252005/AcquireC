"""Tests for proxy_pool module."""

from unittest.mock import MagicMock, patch

import pytest

from src.core.proxy_pool import ProxyError, ProxyPool


class TestProxyPool:
    """Test suite for ProxyPool."""

    def test_get_next_cycles_through_proxies(self) -> None:
        """get_next should cycle through proxies in round-robin order."""
        pool = ProxyPool(proxies=["http://proxy1", "http://proxy2", "http://proxy3"])
        assert pool.get_next() == "http://proxy1"
        assert pool.get_next() == "http://proxy2"
        assert pool.get_next() == "http://proxy3"
        assert pool.get_next() == "http://proxy1"

    def test_mark_failed_skips_proxy_after_max_failures(self) -> None:
        """mark_failed should skip proxy after max_failures is reached."""
        pool = ProxyPool(proxies=["http://proxy1"], max_failures=2)
        pool.mark_failed("http://proxy1")
        assert pool.get_next() == "http://proxy1"
        pool.mark_failed("http://proxy1")
        assert pool.get_next() is None

    def test_mark_success_resets_failure_count(self) -> None:
        """mark_success should reset failure count for a proxy."""
        pool = ProxyPool(proxies=["http://proxy1"], max_failures=2)
        pool.mark_failed("http://proxy1")
        pool.mark_failed("http://proxy1")
        pool.mark_success("http://proxy1")
        assert pool.get_next() == "http://proxy1"

    def test_from_free_proxy_list_returns_proxy_pool(self) -> None:
        """from_free_proxy_list should return a ProxyPool (mock requests.get)."""
        mock_resp = MagicMock()
        mock_resp.text = "192.168.1.1:8080\n192.168.1.2:8080\n"
        mock_resp.raise_for_status.return_value = None
        with patch("src.core.proxy_pool.requests.get", return_value=mock_resp):
            pool = ProxyPool.from_free_proxy_list()
        assert isinstance(pool, ProxyPool)
        assert len(pool.proxies) == 2
        assert pool.proxies[0] == "http://192.168.1.1:8080"
        assert pool.proxies[1] == "http://192.168.1.2:8080"

    def test_from_free_proxy_list_failure_returns_empty_pool(self) -> None:
        """from_free_proxy_list should return empty pool on request failure."""
        with patch("src.core.proxy_pool.requests.get", side_effect=Exception("timeout")):
            pool = ProxyPool.from_free_proxy_list()
        assert isinstance(pool, ProxyPool)
        assert pool.proxies == []

    def test_get_next_returns_none_for_empty_pool(self) -> None:
        """get_next should return None when pool is empty."""
        pool = ProxyPool()
        assert pool.get_next() is None

    def test_add_proxy(self) -> None:
        """add_proxy should append new proxy to the pool."""
        pool = ProxyPool()
        pool.add_proxy("http://proxy1")
        assert pool.proxies == ["http://proxy1"]
        pool.add_proxy("http://proxy1")
        assert len(pool.proxies) == 1

    def test_load_from_file(self, tmp_path) -> None:
        """_load_from_file should read proxies from file, ignoring comments and blanks."""
        proxy_file = tmp_path / "proxies.txt"
        proxy_file.write_text("http://proxy1\n\n# comment\nhttp://proxy2\n")
        pool = ProxyPool(proxy_file=str(proxy_file))
        assert pool.proxies == ["http://proxy1", "http://proxy2"]

    def test_proxy_error_exists(self) -> None:
        """ProxyError should be a subclass of Exception."""
        assert issubclass(ProxyError, Exception)
