"""Google Maps business discovery using Playwright."""

import logging
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, sync_playwright

logger = logging.getLogger(__name__)

from src.vision_mapper import (
    PageMapError,
    build_page_map,
    cleanup_page_map,
    render_page_map,
    safe_click,
    safe_fill,
)


class GoogleMapsScraper:
    """Scrape business listings from Google Maps."""

    def __init__(
        self,
        headless: bool = False,
        timeout: int = 30000,
        browser: Browser | None = None,
    ) -> None:
        self.headless = headless
        self.timeout = timeout
        self.browser = browser
        self.screenshots_dir = Path("screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)

    def discover(
        self,
        city: str,
        category: str,
        max_leads: int = 20,
    ) -> list[dict[str, Any]]:
        """Search Google Maps and return business listings."""
        query = f"{category} in {city}" if category != "all" else f"businesses in {city}"
        results: list[dict[str, Any]] = []

        browser = self.browser
        playwright = None
        if browser is None:
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=self.headless)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            logger.info("Navigating to Google Maps")
            page.goto(
                "https://www.google.com/maps",
                wait_until="domcontentloaded",
                timeout=self.timeout,
            )
            # SPA needs a moment to mount components even after DOM is parsed
            page.wait_for_timeout(3000)

            # ── Consent dialog ────────────────────────────────────────────
            # Handle FIRST because it blocks the entire Maps UI
            logger.info("Checking for cookie/consent dialog")
            consent_handled = False
            for _ in range(3):
                if consent_handled:
                    break
                try:
                    consent_btns = (
                        page.locator('button:has-text("Reject all")')
                        .or_(page.locator('button:has-text("I decline")'))
                        .or_(page.locator('button:has-text("Accept all")'))
                        .or_(page.locator('button:has-text("I agree")'))
                        .or_(page.locator('button:has-text("Consent")'))
                        .or_(page.locator('button:has-text("Continue")'))
                        .or_(page.locator('button:has-text("AGREE")'))
                        .or_(page.locator('button:has-text("Use without accepting")'))
                    )
                    if consent_btns.count() > 0:
                        for btn in consent_btns.all():
                            try:
                                if btn.is_visible(timeout=2000):
                                    logger.info("Clicking consent button")
                                    btn.click(timeout=5000)
                                    time.sleep(1)
                                    consent_handled = True
                                    break
                            except Exception:
                                continue
                    else:
                        break
                except Exception:
                    logger.warning("Consent dialog detection failed")
                    break

            # ── Search box ──────────────────────────────────────────────
            logger.info("Searching for: %s", query)
            search_done = False
            # 1) Try direct selectors with short timeouts so we fail fast
            try:
                search_box = (
                    page.locator('input[id="searchboxinput"]').or_(
                        page.locator('input[aria-label*="Search" i]')
                    ).or_(
                        page.locator('input[placeholder*="Search" i]')
                    ).or_(
                        page.locator('input[placeholder*="search" i]')
                    ).or_(
                        page.locator('input[type="text"]')
                    ).or_(
                        page.locator('[role="combobox"]')
                    ).or_(
                        page.locator('input')
                    )
                )
                sb = search_box.first
                sb.wait_for(state="visible", timeout=5000)
                sb.fill(query, timeout=5000)
                sb.press("Enter", timeout=5000)
                search_done = True
                logger.info("Search filled via direct selector")
            except Exception as search_exc:
                logger.warning("Direct search fill failed: %s", search_exc)

            # 2) Try accessibility-tree fallback
            if not search_done:
                try:
                    safe_fill(
                        page, "searchbox", query,
                        label_hint="Search", placeholder_hint="search"
                    )
                    page.keyboard.press("Enter")
                    search_done = True
                    logger.info("Search filled via accessibility fallback")
                except Exception as mapper_exc:
                    logger.warning("Accessibility fallback failed: %s", mapper_exc)

            # 2b) Try combobox role explicitly (Google Maps uses this now)
            if not search_done:
                try:
                    combobox = page.locator('[role="combobox"]').first
                    combobox.wait_for(state="visible", timeout=5000)
                    combobox.fill(query, timeout=5000)
                    combobox.press("Enter", timeout=5000)
                    search_done = True
                    logger.info("Search filled via combobox selector")
                except Exception as combobox_exc:
                    logger.warning("Combobox fallback failed: %s", combobox_exc)

            if not search_done:
                logger.error("Could not locate or fill the Google Maps search box")
                raise DiscoveryError(
                    "Could not locate or fill the Google Maps search box"
                )
            page.wait_for_timeout(4000)

            # Wait for results list
            logger.info("Waiting for results to load")
            try:
                page.wait_for_selector(
                    'div[role="feed"] > div',
                    timeout=15000,
                )
            except Exception:
                # Try alternative result containers
                alt_selectors = [
                    '[data-result-index]',
                    '[jstcache] div[role="main"]',
                    'div[role="main"] a[href*="/maps/place"]',
                    'div[role="listitem"]',
                    'div[role="main"] div[data-result-index]',
                ]
                for sel in alt_selectors:
                    try:
                        page.wait_for_selector(sel, timeout=5000)
                        logger.info("Results found via selector: %s", sel)
                        break
                    except Exception:
                        continue

            seen_names = set()
            scroll_attempts = 0
            max_scrolls = max_leads * 3
            empty_scrolls = 0

            CARD_SELECTORS = [
                'div[role="feed"] > div',
                'div[role="feed"] a[href*="/maps/place"]',
                '[data-result-index]',
                'a[href*="/maps/place"]',
                'div[role="listitem"]',
                'div[role="main"] div[data-result-index]',
            ]

            # ── Collect place URLs by scrolling ─────────────────────────
            place_urls: list[str] = []
            max_scroll_rounds = max_leads + 5
            for _ in range(max_scroll_rounds):
                if len(place_urls) >= max_leads * 3:
                    break
                found = page.evaluate(
                    """() => {
                        const seen = new Set();
                        const out = [];
                        document.querySelectorAll('a[href*="/maps/place"]').forEach(a => {
                            const href = a.getAttribute('href');
                            if (href && !href.includes('search?') && !href.includes('dir?')) {
                                const clean = href.split('?')[0];
                                if (!seen.has(clean)) {
                                    seen.add(clean);
                                    out.push(clean);
                                }
                            }
                        });
                        return out;
                    }"""
                )
                for url in found:
                    if url not in place_urls:
                        place_urls.append(url)
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(2000)

            logger.info("Collected %d unique place URLs", len(place_urls))
            if not place_urls:
                raise DiscoveryError("No business place URLs found on Google Maps search results.")

            # ── Visit each place page and extract details ────────────────
            for idx, url in enumerate(place_urls):
                if len(results) >= max_leads:
                    break
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                    page.wait_for_timeout(2500)
                    data = self._extract_detail(page)
                    if data and data.get("business_name") and data["business_name"] not in seen_names:
                        seen_names.add(data["business_name"])
                        data["city"] = city
                        data["business_type"] = category
                        data["google_maps_url"] = url
                        results.append(data)
                        logger.info(
                            "[%d/%d] Extracted: %s | phone=%s | website=%s",
                            idx + 1,
                            len(place_urls),
                            data["business_name"],
                            data.get("phone"),
                            data.get("website"),
                        )
                except Exception as visit_exc:
                    logger.warning("Failed to extract from %s: %s", url, visit_exc)
                    continue

        except Exception as exc:
            logger.error("Google Maps scraping failed: %s", exc, exc_info=True)
            timestamp = int(time.time())
            try:
                page.screenshot(path=str(self.screenshots_dir / f"error_{timestamp}.png"))
            except Exception:
                pass
            try:
                nodes = build_page_map(page)
                map_text = render_page_map(nodes)
                map_path = self.screenshots_dir / f"page_map_{timestamp}.txt"
                map_path.write_text(map_text, encoding="utf-8")
                cleanup_page_map(page)
            except Exception:
                pass
            raise DiscoveryError(f"Google Maps scraping failed: {exc}") from exc
        finally:
            context.close()
            if playwright is not None:
                browser.close()
                playwright.stop()

        return results

    def _extract_detail(self, page) -> dict[str, Any] | None:
        """Extract business details from the Google Maps detail panel or page."""
        try:
            page.wait_for_timeout(1500)

            name = ""
            name_selectors = [
                '[role="main"] h1',
                "h1",
                ".DUwDvf",
                ".qBF1Pd",
                "div.fontHeadlineSmall",
            ]
            for sel in name_selectors:
                el = page.locator(sel).first
                if el.count() > 0:
                    name = (el.text_content(timeout=3000) or "").strip()
                    if name and len(name) > 1 and name.lower() not in ("results", "search results", "google maps"):
                        break

            if not name:
                return None

            address = ""
            address_selectors = [
                '[data-item-id="address"]',
                'button[data-item-id="address"]',
                'div[data-item-id="address"]',
                '[role="main"] button:has-text(", Mumbai")',
            ]
            for sel in address_selectors:
                el = page.locator(sel).first
                if el.count() > 0:
                    address = (el.text_content(timeout=2000) or "").strip()
                    if address:
                        break

            phone = ""
            phone_selectors = [
                'a[href^="tel:"]',
                '[data-item-id*="phone" i]',
                'button[aria-label*="phone" i]',
                'a[aria-label*="phone" i]',
            ]
            for sel in phone_selectors:
                el = page.locator(sel).first
                if el.count() > 0:
                    if sel.startswith('a[href^="tel:"]'):
                        phone = (el.get_attribute("href") or "").replace("tel:", "").strip()
                    else:
                        phone = (el.text_content(timeout=2000) or "").strip()
                    if phone:
                        break

            website = ""
            website_selectors = [
                'a[data-item-id*="website" i]',
                'a[aria-label*="Website" i]',
                '[role="main"] a[href^="http"]:not([href*="google"]):not([href*="maps"])',
            ]
            for sel in website_selectors:
                el = page.locator(sel).first
                if el.count() > 0:
                    href = (el.get_attribute("href") or "").strip()
                    if href and href.startswith("http") and "google" not in href:
                        website = href
                        break
                    text = (el.text_content(timeout=2000) or "").strip()
                    if text and text.startswith("http") and "google" not in text:
                        website = text
                        break

            # Rating & reviews
            rating: float | None = None
            review_count: int | None = None
            try:
                # Google Maps shows rating like "4.5" near reviews count
                rating_text = page.locator('[role="main"] span:has-text(".")').first.text_content(timeout=2000) or ""
                # Try broader selectors
                if not rating_text or "." not in rating_text:
                    rating_text = page.locator('div.fontDisplayLarge, div[role="main"] span[aria-hidden="true"]').first.text_content(timeout=2000) or ""
                rating_match = __import__('re').search(r"(\d\.\d)", rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            except Exception:
                pass

            try:
                reviews_text = page.locator('[role="main"] a:has-text("review")').first.text_content(timeout=2000) or ""
                if not reviews_text:
                    reviews_text = page.locator('[role="main"] span:has-text("(")').first.text_content(timeout=2000) or ""
                reviews_match = __import__('re').search(r"[\(]?([\d,]+)\s*review", reviews_text)
                if reviews_match:
                    review_count = int(reviews_match.group(1).replace(",", ""))
            except Exception:
                pass

            # Price level ($ to $$$$)
            price_level: str | None = None
            try:
                price_text = page.locator('[role="main"] span:has-text("$")').first.text_content(timeout=2000) or ""
                if "$" in price_text:
                    price_level = "".join(c for c in price_text if c == "$")
                    if not price_level:
                        # Try aria-label approach
                        price_els = page.locator('[aria-label*="$"]').all()
                        for pel in price_els:
                            label = pel.get_attribute("aria-label") or ""
                            pl = "".join(c for c in label if c == "$")
                            if pl:
                                price_level = pl
                                break
            except Exception:
                pass

            maps_url = ""
            try:
                url = page.url
                if "/maps/place/" in url:
                    maps_url = url.split("?")[0]
            except Exception:
                pass

            # Strip Google Maps material-icon unicode prefixes
            def _clean(t: str) -> str:
                return "".join(c for c in (t or "") if ord(c) < 0xE000 or ord(c) > 0xF8FF).strip()

            return {
                "business_name": _clean(name),
                "address": _clean(address),
                "phone": _clean(phone) or None,
                "email": None,
                "website": website or None,
                "google_maps_url": maps_url or "",
                "rating": rating,
                "review_count": review_count,
                "price_level": price_level,
            }
        except Exception as exc:
            logger.debug("Detail extraction failed: %s", exc)
            return None


class DiscoveryError(Exception):
    """Raised when discovery fails."""
