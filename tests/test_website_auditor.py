"""Tests for website auditor module."""

from unittest.mock import MagicMock, patch

import pytest

from src.website_auditor import WebsiteAuditor


def _build_mock_page(
    url: str = "https://example.com",
    node_count: int = 500,
    perf_timing: dict | None = None,
    viewport_count: int = 1,
    generator_content: str = "",
    img_count: int = 0,
    table_count: int = 0,
    presentation_table_count: int = 0,
    deprecated_counts: dict[str, int] | None = None,
) -> MagicMock:
    """Build a robust mock Playwright page that survives desktop+mobile runs."""
    deprecated_counts = deprecated_counts or {}
    page = MagicMock()
    page.goto = MagicMock()
    page.wait_for_load_state = MagicMock()
    page.url = url
    page.evaluate.side_effect = [node_count, perf_timing, node_count, perf_timing]

    def make_locator(selector: str) -> MagicMock:
        loc = MagicMock()
        if 'meta[name="viewport"]' in selector:
            loc.count.return_value = viewport_count
        elif 'meta[name="generator"]' in selector:
            first = MagicMock()
            first.count.return_value = 1 if generator_content else 0
            first.get_attribute.return_value = generator_content
            loc.first = first
        elif selector == "img":
            loc.count.return_value = img_count
            loc.all.return_value = []
        elif selector == "table":
            loc.count.return_value = table_count
        elif selector == 'table[role="presentation"]':
            loc.count.return_value = presentation_table_count
        elif selector in ("font", "marquee", "blink", "center"):
            loc.count.return_value = deprecated_counts.get(selector, 0)
        else:
            loc.count.return_value = 0
            loc.all.return_value = []
        return loc

    page.locator.side_effect = make_locator
    return page


def _patch_sync_playwright(mock_page: MagicMock) -> None:
    """Patch sync_playwright to return a mock browser that yields *mock_page*."""
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_playwright = MagicMock()
    mock_playwright.chromium.launch.return_value = mock_browser

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_playwright)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


class TestWebsiteAuditor:
    """Test suite for WebsiteAuditor."""

    def test_init(self) -> None:
        """Should initialize with defaults."""
        auditor = WebsiteAuditor()
        assert auditor.headless is True
        assert auditor.timeout == 30000

    def test_audit_returns_dict(self) -> None:
        """audit should return a dict with expected keys."""
        auditor = WebsiteAuditor()
        mock_page = _build_mock_page(
            url="https://example.com",
            node_count=500,
            perf_timing={"navStart": 1000, "loadEnd": 2500},
            viewport_count=1,
        )
        mock_ctx = _patch_sync_playwright(mock_page)

        with patch("src.website_auditor.sync_playwright", return_value=mock_ctx):
            result = auditor.audit("https://example.com")

        assert isinstance(result, dict)
        assert result["has_website"] is True
        assert result["https"] is True
        assert result["overall_score"] in ("good", "needs_work", "poor")
        assert "mobile_friendly" in result
        assert "load_time_ms" in result
        assert "old_tech_detected" in result
        assert "layout_issues" in result

    def test_audit_flags_missing_viewport(self) -> None:
        """Should flag missing viewport meta tag."""
        auditor = WebsiteAuditor()
        mock_page = _build_mock_page(
            url="https://oldsite.com",
            node_count=200,
            perf_timing=None,
            viewport_count=0,
        )
        mock_ctx = _patch_sync_playwright(mock_page)

        with patch("src.website_auditor.sync_playwright", return_value=mock_ctx):
            result = auditor.audit("https://oldsite.com")

        assert result["mobile_friendly"] is False
        assert "missing_viewport_meta" in result["layout_issues"]

    def test_audit_flags_old_tech(self) -> None:
        """Should detect FrontPage/Dreamweaver generator meta."""
        auditor = WebsiteAuditor()
        mock_page = _build_mock_page(
            url="https://legacy.com",
            node_count=150,
            perf_timing=None,
            generator_content="Microsoft FrontPage 5.0",
        )
        mock_ctx = _patch_sync_playwright(mock_page)

        with patch("src.website_auditor.sync_playwright", return_value=mock_ctx):
            result = auditor.audit("https://legacy.com")

        assert "microsoft frontpage" in result["old_tech_detected"]

    def test_audit_handles_exception(self) -> None:
        """Should return audit_failed=True on exception."""
        auditor = WebsiteAuditor()
        with patch("src.website_auditor.sync_playwright") as mock_sync:
            mock_sync.side_effect = Exception("Browser crash")
            result = auditor.audit("https://bad.com")

        assert result["has_website"] is True
        assert result.get("audit_failed") is True

    def test_audit_platform_page(self) -> None:
        """Should mark Swiggy/Zomato URLs as platform_page with poor score."""
        auditor = WebsiteAuditor()
        result = auditor.audit("https://www.swiggy.com/restaurants/foo")

        assert result.get("platform_page") is True
        assert result["overall_score"] == "poor"
        assert "platform_page_not_real_website" in result["layout_issues"]

    def test_audit_modern_cms_leniency(self) -> None:
        """Should score modern CMS sites as good even with minor bloat."""
        auditor = WebsiteAuditor()
        mock_page = _build_mock_page(
            url="https://nextjs-shop.com",
            node_count=3500,  # would normally trigger bloat
            perf_timing={"navStart": 1000, "loadEnd": 2500},
            viewport_count=1,
        )
        # Inject nextjs marker into page content so _detect_cms_from_html picks it up
        mock_page.content.return_value = '<html><script>__NEXT_DATA__ = {}</script></html>'
        mock_ctx = _patch_sync_playwright(mock_page)

        with patch("src.website_auditor.sync_playwright", return_value=mock_ctx):
            result = auditor.audit("https://nextjs-shop.com")

        assert result["detected_cms"] == "nextjs"
        assert result["overall_score"] == "good"

    def test_audit_social_media_link(self) -> None:
        """Should mark Instagram/LinkedIn URLs as social_media with poor score."""
        auditor = WebsiteAuditor()
        result = auditor.audit("https://instagram.com/kgcafe")

        assert result.get("social_media") is True
        assert result["overall_score"] == "poor"
        assert "social_media_link_not_real_website" in result["layout_issues"]
        assert result["has_website"] is False
