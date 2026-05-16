"""Website quality auditor for evaluating existing business sites."""

from __future__ import annotations

import time
from typing import Any

from playwright.sync_api import sync_playwright


class WebsiteAuditor:
    """Audit a business website for quality signals (mobile, speed, tech stack)."""

    def __init__(self, headless: bool = True, timeout: int = 30000) -> None:
        self.headless = headless
        self.timeout = timeout

    def audit(self, url: str) -> dict[str, Any]:
        """Run a multi-viewport audit on *url* and return a quality report dict.

        Returns on error: {"has_website": True, "audit_failed": True}
        """
        result: dict[str, Any] = {
            "has_website": True,
            "mobile_friendly": True,
            "https": url.startswith("https://"),
            "load_time_ms": 0,
            "old_tech_detected": [],
            "layout_issues": [],
            "overall_score": "good",
            "detected_cms": None,
        }

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                try:
                    # --- Desktop audit ---
                    desktop_ctx = browser.new_context(
                        viewport={"width": 1280, "height": 800},
                    )
                    desktop_page = desktop_ctx.new_page()
                    _run_checks(desktop_page, url, result, self.timeout)
                    desktop_ctx.close()

                    # --- Mobile audit ---
                    mobile_ctx = browser.new_context(
                        viewport={"width": 375, "height": 667},
                        user_agent=(
                            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                            "Version/16.0 Mobile/15E148 Safari/604.1"
                        ),
                    )
                    mobile_page = mobile_ctx.new_page()
                    _run_checks(mobile_page, url, result, self.timeout, is_mobile=True)
                    mobile_ctx.close()
                finally:
                    browser.close()
        except Exception:
            return {"has_website": True, "audit_failed": True}

        # --- Heuristic scoring ---
        issues = len(result["old_tech_detected"]) + len(result["layout_issues"])
        if not result["https"]:
            issues += 1
        if result["load_time_ms"] > 5000:
            issues += 1
        if not result["mobile_friendly"]:
            issues += 1

        if issues >= 3 or result["load_time_ms"] > 8000:
            result["overall_score"] = "poor"
        elif issues >= 1:
            result["overall_score"] = "needs_work"
        else:
            result["overall_score"] = "good"

        return result


def _run_checks(
    page,
    url: str,
    result: dict[str, Any],
    timeout: int,
    is_mobile: bool = False,
) -> None:
    """Navigate and run technical checks on a single page instance."""
    start = time.time()
    page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    page.wait_for_load_state("networkidle", timeout=timeout)
    load_ms = int((time.time() - start) * 1000)
    result["load_time_ms"] = max(result["load_time_ms"], load_ms)

    # 1. Viewport meta tag
    viewport_exists = page.locator('meta[name="viewport"]').count() > 0
    if is_mobile and not viewport_exists:
        result["mobile_friendly"] = False
        result["layout_issues"].append("missing_viewport_meta")

    # 2. HTTPS check (already set from URL but double-check current URL)
    current_url = page.url
    if not current_url.startswith("https://"):
        result["https"] = False
        result["layout_issues"].append("no_https")

    # 3. DOM size
    node_count = page.evaluate("() => document.querySelectorAll('*').length")
    if node_count > 3000:
        result["layout_issues"].append(f"bloated_dom_{node_count}_nodes")

    # 4. Tables used for layout
    table_count = page.locator("table").count()
    presentation_tables = page.locator('table[role="presentation"]').count()
    layout_tables = table_count - presentation_tables
    if layout_tables > 2:
        result["layout_issues"].append(f"tables_for_layout_{layout_tables}")

    # 5. Responsive images
    images = page.locator("img").all()
    non_responsive = 0
    for img in images:
        try:
            has_srcset = img.get_attribute("srcset") or ""
            has_sizes = img.get_attribute("sizes") or ""
            if not has_srcset and not has_sizes:
                non_responsive += 1
        except Exception:
            continue
    if len(images) > 20 and non_responsive > len(images) * 0.5:
        result["layout_issues"].append(f"non_responsive_images_{non_responsive}/{len(images)}")

    # 6. Old tech signatures
    generator = page.locator('meta[name="generator"]').first
    detected_cms = None
    if generator.count() > 0:
        gen_content = (generator.get_attribute("content") or "").lower()
        ancient = ["frontpage", "dreamweaver", "iweb", "wordpress 3.", "wordpress 2.", "wordpress 1.", "microsoft frontpage", "adobe golive"]
        for sig in ancient:
            if sig in gen_content:
                result["old_tech_detected"].append(sig)
        # CMS detection
        if "wordpress" in gen_content:
            detected_cms = "wordpress"
        elif "wix" in gen_content:
            detected_cms = "wix"
        elif "squarespace" in gen_content:
            detected_cms = "squarespace"
        elif "shopify" in gen_content:
            detected_cms = "shopify"
        elif "drupal" in gen_content:
            detected_cms = "drupal"
        elif "joomla" in gen_content:
            detected_cms = "joomla"

    # Detect CMS from other signals if meta generator didn't catch it
    if not detected_cms:
        try:
            html = page.content()
            if "wp-content" in html or "wp-includes" in html:
                detected_cms = "wordpress"
            elif "wix.com" in html or "wix-static" in html:
                detected_cms = "wix"
            elif "squarespace.com" in html or "sqsp" in html:
                detected_cms = "squarespace"
            elif "cdn.shopify.com" in html or "myshopify" in html:
                detected_cms = "shopify"
            elif "react-root" in html and "next.js" not in html.lower():
                detected_cms = "custom"
        except Exception:
            pass

    result["detected_cms"] = detected_cms

    # Check for very old inline styles / font tags / marquee / blink
    deprecated_tags = ["font", "marquee", "blink", "center"]
    for tag in deprecated_tags:
        if page.locator(tag).count() > 0:
            result["old_tech_detected"].append(f"deprecated_tag_{tag}")

    # 7. Performance timing via JS (if available)
    try:
        perf = page.evaluate("""() => {
            const t = window.performance && window.performance.timing;
            if (!t) return null;
            return {
                navStart: t.navigationStart,
                loadEnd: t.loadEventEnd,
            };
        }""")
        if perf and perf.get("loadEnd") and perf.get("navStart"):
            js_load = perf["loadEnd"] - perf["navStart"]
            if js_load > 0:
                result["load_time_ms"] = max(result["load_time_ms"], js_load)
                if js_load > 5000:
                    result["layout_issues"].append(f"slow_load_{js_load}ms")
    except Exception:
        pass
