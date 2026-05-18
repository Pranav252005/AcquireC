"""Website quality auditor for evaluating existing business sites."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import Browser, sync_playwright

from src.filters import LeadQualityFilter

logger = logging.getLogger(__name__)

# Simple in-memory cache for audit results
_audit_cache: dict[str, dict[str, Any]] = {}


def _get_from_cache(url: str) -> dict[str, Any] | None:
    return _audit_cache.get(url)


def _set_cache(url: str, result: dict[str, Any]) -> None:
    _audit_cache[url] = result


class WebsiteAuditor:
    """Audit a business website for quality signals (mobile, speed, tech stack)."""

    def __init__(self, headless: bool = True, timeout: int = 30000, browser: Browser | None = None) -> None:
        self.headless = headless
        self.timeout = timeout
        self.browser = browser

    def audit(self, url: str) -> dict[str, Any]:
        """Run an audit on *url* and return a quality report dict.

        Returns on error: {"has_website": True, "audit_failed": True}
        """
        cached = _get_from_cache(url)
        if cached is not None:
            return cached

        # Platform pages (Swiggy, Zomato, etc.) are not real business websites
        if LeadQualityFilter.is_platform_only_website(url):
            result: dict[str, Any] = {
                "has_website": True,
                "mobile_friendly": True,
                "https": url.startswith("https://"),
                "load_time_ms": 0,
                "old_tech_detected": [],
                "layout_issues": ["platform_page_not_real_website"],
                "overall_score": "poor",
                "detected_cms": None,
                "platform_page": True,
            }
            _set_cache(url, result)
            return result

        result = {
            "has_website": True,
            "mobile_friendly": True,
            "https": url.startswith("https://"),
            "load_time_ms": 0,
            "old_tech_detected": [],
            "layout_issues": [],
            "overall_score": "good",
            "detected_cms": None,
        }

        # Fast path: requests + BeautifulSoup
        try:
            self._audit_with_requests(url, result)
            # If we got enough info and no heavy JS detected, skip Playwright
            if result.get("detected_cms") or result["layout_issues"] or not result.get("needs_js", False):
                self._score(result)
                _set_cache(url, result)
                return result
        except Exception as exc:
            logger.debug("Requests fast-path audit failed for %s: %s", url, exc)

        # Playwright path for JS-heavy sites
        try:
            self._audit_with_playwright(url, result)
        except Exception as exc:
            logger.warning("Playwright audit failed for %s: %s", url, exc)
            _set_cache(url, {"has_website": True, "audit_failed": True})
            return {"has_website": True, "audit_failed": True}

        self._score(result)
        _set_cache(url, result)
        return result

    def _audit_with_requests(self, url: str, result: dict[str, Any]) -> None:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Viewport meta
        viewport = soup.find("meta", attrs={"name": "viewport"})
        if not viewport:
            result["mobile_friendly"] = False
            result["layout_issues"].append("missing_viewport_meta")

        # HTTPS check
        if not resp.url.startswith("https://"):
            result["https"] = False
            result["layout_issues"].append("no_https")

        # DOM size (approximate from HTML length / tag count)
        dom_size = len(soup.find_all(True))
        if dom_size > 3000:
            result["layout_issues"].append(f"bloated_dom_{dom_size}_nodes")

        # Tables for layout
        tables = soup.find_all("table")
        presentation_tables = len(soup.find_all("table", attrs={"role": "presentation"}))
        layout_tables = len(tables) - presentation_tables
        if layout_tables > 2:
            result["layout_issues"].append(f"tables_for_layout_{layout_tables}")

        # Responsive images
        images = soup.find_all("img")
        non_responsive = sum(1 for img in images if not img.get("srcset") and not img.get("sizes"))
        if len(images) > 20 and non_responsive > len(images) * 0.5:
            result["layout_issues"].append(f"non_responsive_images_{non_responsive}/{len(images)}")

        # CMS detection
        result["detected_cms"] = self._detect_cms(soup, resp.text)

        # Old tech
        generator = soup.find("meta", attrs={"name": "generator"})
        if generator:
            gen_content = (generator.get("content") or "").lower()
            ancient = ["frontpage", "dreamweaver", "iweb", "wordpress 3.", "wordpress 2.", "wordpress 1.", "microsoft frontpage", "adobe golive"]
            for sig in ancient:
                if sig in gen_content:
                    result["old_tech_detected"].append(sig)

        for tag in ["font", "marquee", "blink", "center"]:
            if soup.find(tag):
                result["old_tech_detected"].append(f"deprecated_tag_{tag}")

        # Modern framework detection
        if "__NEXT_DATA__" in resp.text:
            result["detected_cms"] = "nextjs"
        elif "astro-island" in resp.text:
            result["detected_cms"] = "astro"
        elif "data-reactroot" in resp.text or "reactroot" in resp.text:
            result["detected_cms"] = "react"
        elif "__VUE__" in resp.text:
            result["detected_cms"] = "vue"
        elif "window.gatsby" in resp.text or "___gatsby" in resp.text:
            result["detected_cms"] = "gatsby"

        # Flag if we might need JS rendering
        result["needs_js"] = bool(result["detected_cms"] in ("nextjs", "react", "vue", "gatsby", "astro"))

    def _audit_with_playwright(self, url: str, result: dict[str, Any]) -> None:
        browser = self.browser
        if browser is None:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                self._run_playwright_checks(browser, url, result)
        else:
            self._run_playwright_checks(browser, url, result)

    @staticmethod
    def _run_playwright_checks(browser, url: str, result: dict[str, Any]) -> None:
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        start = time.time()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=30000)
        result["load_time_ms"] = int((time.time() - start) * 1000)

        viewport_exists = page.locator('meta[name="viewport"]').count() > 0
        if not viewport_exists:
            result["mobile_friendly"] = False
            result["layout_issues"].append("missing_viewport_meta")

        current_url = page.url
        if not current_url.startswith("https://"):
            result["https"] = False
            result["layout_issues"].append("no_https")

        node_count = page.evaluate("() => document.querySelectorAll('*').length")
        if node_count > 3000:
            result["layout_issues"].append(f"bloated_dom_{node_count}_nodes")

        table_count = page.locator("table").count()
        presentation_tables = page.locator('table[role="presentation"]').count()
        layout_tables = table_count - presentation_tables
        if layout_tables > 2:
            result["layout_issues"].append(f"tables_for_layout_{layout_tables}")

        images = page.locator("img").all()
        non_responsive = 0
        for img in images:
            try:
                if not img.get_attribute("srcset") and not img.get_attribute("sizes"):
                    non_responsive += 1
            except Exception as exc:
                logger.debug("Image responsive check failed: %s", exc)
                continue
        if len(images) > 20 and non_responsive > len(images) * 0.5:
            result["layout_issues"].append(f"non_responsive_images_{non_responsive}/{len(images)}")

        html = page.content()
        result["detected_cms"] = WebsiteAuditor._detect_cms_from_html(html)

        generator = page.locator('meta[name="generator"]').first
        if generator.count() > 0:
            gen_content = (generator.get_attribute("content") or "").lower()
            ancient = ["frontpage", "dreamweaver", "iweb", "wordpress 3.", "wordpress 2.", "wordpress 1.", "microsoft frontpage", "adobe golive"]
            for sig in ancient:
                if sig in gen_content:
                    result["old_tech_detected"].append(sig)

        for tag in ["font", "marquee", "blink", "center"]:
            if page.locator(tag).count() > 0:
                result["old_tech_detected"].append(f"deprecated_tag_{tag}")

        try:
            perf = page.evaluate("""() => {
                const t = window.performance && window.performance.timing;
                if (!t) return null;
                return { navStart: t.navigationStart, loadEnd: t.loadEventEnd };
            }""")
            if perf and perf.get("loadEnd") and perf.get("navStart"):
                js_load = perf["loadEnd"] - perf["navStart"]
                if js_load > 0:
                    result["load_time_ms"] = max(result["load_time_ms"], js_load)
                    if js_load > 5000:
                        result["layout_issues"].append(f"slow_load_{js_load}ms")
        except Exception as exc:
            logger.debug("Performance timing extraction failed: %s", exc)

        context.close()

    @staticmethod
    def _detect_cms(soup: BeautifulSoup, html: str) -> str | None:
        generator = soup.find("meta", attrs={"name": "generator"})
        if generator:
            gen = (generator.get("content") or "").lower()
            if "wordpress" in gen:
                return "wordpress"
            if "wix" in gen:
                return "wix"
            if "squarespace" in gen:
                return "squarespace"
            if "shopify" in gen:
                return "shopify"
            if "drupal" in gen:
                return "drupal"
            if "joomla" in gen:
                return "joomla"
        if "wp-content" in html or "wp-includes" in html:
            return "wordpress"
        if "wix.com" in html or "wix-static" in html:
            return "wix"
        if "squarespace.com" in html or "sqsp" in html:
            return "squarespace"
        if "cdn.shopify.com" in html or "myshopify" in html:
            return "shopify"
        return None

    @staticmethod
    def _detect_cms_from_html(html: str) -> str | None:
        if "wp-content" in html or "wp-includes" in html:
            return "wordpress"
        if "wix.com" in html or "wix-static" in html:
            return "wix"
        if "squarespace.com" in html or "sqsp" in html:
            return "squarespace"
        if "cdn.shopify.com" in html or "myshopify" in html:
            return "shopify"
        if "__NEXT_DATA__" in html:
            return "nextjs"
        if "astro-island" in html:
            return "astro"
        if "data-reactroot" in html or "reactroot" in html:
            return "react"
        if "__VUE__" in html:
            return "vue"
        if "window.gatsby" in html or "___gatsby" in html:
            return "gatsby"
        return None

    @staticmethod
    def _score(result: dict[str, Any]) -> None:
        issues = len(result["old_tech_detected"]) + len(result["layout_issues"])

        # Modern framework/CMS penalty reduction
        modern_cms = {"nextjs", "astro", "react", "vue", "gatsby", "shopify", "squarespace", "wix"}
        cms = result.get("detected_cms")
        is_modern = cms in modern_cms

        if not result["https"]:
            issues += 1
        if result["load_time_ms"] > 5000 and not is_modern:
            issues += 1
        if result["load_time_ms"] > 8000:
            issues += 1  # always bad regardless of CMS
        if not result["mobile_friendly"]:
            issues += 1
        if result.get("platform_page"):
            issues += 2

        # DOM bloat is less severe for modern frameworks (hydration bloat)
        dom_bloat = any("bloated_dom" in i for i in result["layout_issues"])
        if dom_bloat and is_modern:
            issues -= 1

        if issues >= 3 or result["load_time_ms"] >= 8000 or result.get("platform_page"):
            result["overall_score"] = "poor"
        elif issues >= 1:
            result["overall_score"] = "needs_work"
        else:
            result["overall_score"] = "good"
