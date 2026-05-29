"""Tests for the online website verifier."""

from unittest.mock import MagicMock, patch

import pytest

from src.website_verifier import WebsiteVerifier, _is_ignored_host


class TestIsIgnoredHost:
    """Test suite for the _is_ignored_host helper."""

    def test_google_hosts_ignored(self):
        assert _is_ignored_host("google.com")
        assert _is_ignored_host("www.google.com")
        assert _is_ignored_host("maps.google.com")

    def test_social_hosts_ignored(self):
        assert _is_ignored_host("instagram.com")
        assert _is_ignored_host("facebook.com")

    def test_real_host_not_ignored(self):
        assert not _is_ignored_host("example.com")
        assert not _is_ignored_host("kgcafe.in")


class TestWebsiteVerifier:
    """Test suite for WebsiteVerifier."""

    def test_verify_returns_dict(self):
        verifier = WebsiteVerifier(delay_seconds=0)
        with patch.object(verifier, "_search_duckduckgo", return_value={
            "has_real_website": False,
            "found_url": None,
            "source": "duckduckgo",
        }):
            result = verifier.verify("Some Business", "Mumbai")
        assert isinstance(result, dict)
        assert "has_real_website" in result

    def test_extract_real_url_unwraps_ddg_redirect(self):
        href = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage&rut=abc"
        assert WebsiteVerifier._extract_real_url(href) == "https://example.com/page"

    def test_extract_real_url_passes_through_direct(self):
        href = "https://example.com/page"
        assert WebsiteVerifier._extract_real_url(href) == href

    def test_search_finds_real_website(self):
        """When DDG returns a result with a real domain, verifier should flag it."""
        verifier = WebsiteVerifier(delay_seconds=0)

        fake_html = """
        <div class="result">
            <a class="result__a" href="https://example.com">Sharma Sweets — Home</a>
            <div class="result__snippet">Welcome to Sharma Sweets in Mumbai</div>
        </div>
        """
        with patch("src.website_verifier.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.text = fake_html
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            result = verifier._search_duckduckgo(
                '"Sharma Sweets" "Mumbai"', "Sharma Sweets", "Mumbai"
            )

        assert result["has_real_website"] is True
        assert result["found_url"] == "https://example.com"
        assert result["source"] == "duckduckgo"

    def test_search_ignores_social_media(self):
        """Social-media links in search results must not count as a real website."""
        verifier = WebsiteVerifier(delay_seconds=0)

        fake_html = """
        <div class="result">
            <a class="result__a" href="https://instagram.com/sharmasweets">Sharma Sweets</a>
        </div>
        """
        with patch("src.website_verifier.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.text = fake_html
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            result = verifier._search_duckduckgo(
                '"Sharma Sweets" "Mumbai"', "Sharma Sweets", "Mumbai"
            )

        assert result["has_real_website"] is False
        assert result["found_url"] is None

    def test_search_ignores_google_maps(self):
        """Google Maps links in search results must not count as a real website."""
        verifier = WebsiteVerifier(delay_seconds=0)

        fake_html = """
        <div class="result">
            <a class="result__a" href="https://www.google.com/maps/place/Sharma+Sweets">Map</a>
        </div>
        """
        with patch("src.website_verifier.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.text = fake_html
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            result = verifier._search_duckduckgo(
                '"Sharma Sweets" "Mumbai"', "Sharma Sweets", "Mumbai"
            )

        assert result["has_real_website"] is False

    def test_search_requires_name_match(self):
        """A random domain that does not mention the business name should be ignored."""
        verifier = WebsiteVerifier(delay_seconds=0)

        fake_html = """
        <div class="result">
            <a class="result__a" href="https://totally-unrelated.com">Unrelated Page</a>
        </div>
        """
        with patch("src.website_verifier.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.text = fake_html
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            result = verifier._search_duckduckgo(
                '"Sharma Sweets" "Mumbai"', "Sharma Sweets", "Mumbai"
            )

        assert result["has_real_website"] is False

    def test_search_handles_request_error(self):
        """Network errors should return a safe 'no website' response."""
        verifier = WebsiteVerifier(delay_seconds=0)

        with patch("src.website_verifier.requests.post", side_effect=Exception("timeout")):
            result = verifier._search_duckduckgo(
                '"Sharma Sweets" "Mumbai"', "Sharma Sweets", "Mumbai"
            )

        assert result["has_real_website"] is False
        assert result["found_url"] is None
        assert result["source"] == "error"
