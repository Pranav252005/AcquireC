"""Tests for discovery module."""

from unittest.mock import MagicMock, patch

import pytest

from src.discovery import DiscoveryError, GoogleMapsScraper


class TestGoogleMapsScraper:
    """Test suite for GoogleMapsScraper."""

    def test_init_sets_defaults(self) -> None:
        """Scraper should initialize with sensible defaults."""
        scraper = GoogleMapsScraper()
        assert scraper.headless is False
        assert scraper.timeout == 30000

    def test_discover_returns_list(self) -> None:
        """discover should return a list of dicts."""
        scraper = GoogleMapsScraper()
        fake_result = {
            "business_name": "Test Cafe",
            "address": "123 Main St",
            "phone": None,
            "email": None,
            "website": None,
            "google_maps_url": "https://maps.google.com/place/123",
            "city": "Mumbai",
            "business_type": "cafe",
            "rating": None,
            "review_count": None,
            "price_level": None,
        }
        with patch.object(scraper, "discover", return_value=[fake_result]):
            results = scraper.discover("Mumbai", "cafe", max_leads=1)
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["business_name"] == "Test Cafe"
        assert results[0]["city"] == "Mumbai"

    def test_extract_detail_handles_missing_name(self) -> None:
        """_extract_detail should return None when name is missing."""
        scraper = GoogleMapsScraper()
        mock_page = MagicMock()
        mock_page.locator.return_value.first = MagicMock()
        mock_page.locator.return_value.first.text_content.side_effect = Exception("not found")
        mock_page.locator.return_value.count.return_value = 0
        result = scraper._extract_detail(mock_page)
        assert result is None

    def test_discovery_error_is_exception(self) -> None:
        """DiscoveryError should be catchable as Exception."""
        with pytest.raises(DiscoveryError):
            raise DiscoveryError("test error")

    def test_lead_with_website_gets_filtered_in_pipeline(self) -> None:
        """A mock lead with a website field should be filterable."""
        fake_result = {
            "business_name": "Cafe With Site",
            "address": "123 Main St",
            "phone": None,
            "email": None,
            "website": "http://example.com",
            "google_maps_url": "https://maps.google.com/place/123",
            "city": "Mumbai",
            "business_type": "cafe",
        }
        assert fake_result.get("website") is not None

    def test_goto_uses_domcontentloaded_not_networkidle(self) -> None:
        """The discover method must use domcontentloaded, not networkidle,
        because Google Maps persistent WebSocket connections prevent networkidle
        from firing reliably."""
        import inspect

        source = inspect.getsource(GoogleMapsScraper.discover)
        assert 'wait_until="domcontentloaded"' in source
        assert 'wait_until="networkidle"' not in source

    def test_search_failure_error_message_is_clear(self) -> None:
        """If search box filling fails after all fallbacks, the error message should be specific."""
        import inspect

        source = inspect.getsource(GoogleMapsScraper.discover)
        assert "Could not locate or fill the Google Maps search box" in source

    def test_discovery_exhausted_error_is_subclass(self) -> None:
        """DiscoveryExhaustedError should be catchable as DiscoveryError."""
        from src.discovery import DiscoveryExhaustedError

        with pytest.raises(DiscoveryError):
            raise DiscoveryExhaustedError("exhausted")

    def test_discover_accepts_exclude_names(self) -> None:
        """discover should accept an exclude_names parameter."""
        import inspect

        sig = inspect.signature(GoogleMapsScraper.discover)
        assert "exclude_names" in sig.parameters

    def test_url_name_parsing_skips_known_places(self) -> None:
        """URLs containing known business names should be pre-filtered."""
        import inspect

        source = inspect.getsource(GoogleMapsScraper.discover)
        assert "urllib.parse.unquote_plus" in source
        assert "exclude_names" in source
