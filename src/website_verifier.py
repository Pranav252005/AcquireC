"""Online website verification for businesses discovered without a listed website.

When Google Maps does not list a website for a business, this module searches
the open web (DuckDuckGo) to see whether the business actually owns a real
domain.  This prevents us from pitching a website to a lead that already has
one, which was the #1 accuracy complaint.
"""

from __future__ import annotations

import logging
import time
import urllib.parse
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.filters import LeadQualityFilter

logger = logging.getLogger(__name__)

# Hosts that appear in search results but are NOT a business's own website
_IGNORED_SEARCH_HOSTS: set[str] = {
    "google.com",
    "google.co.in",
    "google.co.uk",
    "maps.google.com",
    "youtube.com",
    "yelp.com",
    "tripadvisor.com",
    "tripadvisor.in",
    "justdial.com",
    "indiamart.com",
    "sulekha.com",
    "practo.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "pinterest.com",
    "reddit.com",
    "quora.com",
    "zomato.com",
    "swiggy.com",
    "ubereats.com",
    "doordash.com",
    "grubhub.com",
    "deliveroo.com",
    "foodpanda.com",
    "restaurant-guru.in",
    "dineout.co.in",
    "eazydiner.com",
    "magicpin.in",
    "nearbuy.com",
    "urbancompany.com",
    "yappe.in",
    "crowndevour.com",
    "weddingwire.in",
    "wedmegood.com",
    "venuelook.com",
    "foursquare.com",
    "yellowpages.com",
    "bing.com",
    "mapquest.com",
    "amazon.in",
    "amazon.com",
    "flipkart.com",
}


def _is_ignored_host(hostname: str) -> bool:
    """Return True if the hostname is a search engine, maps, review site, or directory."""
    h = hostname.lower().lstrip("www.")
    return any(h == ign or h.endswith(f".{ign}") for ign in _IGNORED_SEARCH_HOSTS)


class WebsiteVerifier:
    """Verify whether a business has a real website by searching online."""

    def __init__(self, delay_seconds: float = 1.5) -> None:
        self.delay_seconds = delay_seconds

    def verify(
        self,
        business_name: str,
        city: str,
    ) -> dict[str, Any]:
        """Search the web for *business_name* in *city* and report whether a
        real business website was found.

        Returns:
            A dict with keys:
                - ``has_real_website`` (bool)
                - ``found_url`` (str | None)
                - ``source`` (str) — ``"duckduckgo"`` or ``"error"``
        """
        query = f'"{business_name}" "{city}"'
        result = self._search_duckduckgo(query, business_name, city)

        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

        return result

    def _search_duckduckgo(
        self,
        query: str,
        business_name: str,
        city: str,
    ) -> dict[str, Any]:
        """Query DuckDuckGo HTML and inspect the first few organic results."""
        try:
            resp = requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query, "kl": "us-en"},
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://html.duckduckgo.com/",
                },
                timeout=20,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("DuckDuckGo request failed for '%s': %s", query, exc)
            return {
                "has_real_website": False,
                "found_url": None,
                "source": "error",
            }

        soup = BeautifulSoup(resp.text, "html.parser")

        # DuckDuckGo HTML uses .result or .web-result wrappers
        result_els = soup.select(".result") or soup.select(".web-result")
        if not result_els:
            result_els = soup.find_all("div", class_=lambda c: c and "result" in c)

        name_lower = business_name.lower()
        name_tokens = [t for t in name_lower.split() if len(t) > 2]

        for el in result_els[:5]:
            link_el = el.select_one("a.result__a") or el.find("a")
            if not link_el:
                continue

            href = link_el.get("href", "")
            if not href:
                continue

            real_url = self._extract_real_url(href)
            if not real_url or not real_url.startswith("http"):
                continue

            # Skip Google Maps, review sites, social media, platforms
            parsed = urllib.parse.urlparse(real_url)
            hostname = parsed.hostname or ""
            if _is_ignored_host(hostname):
                continue
            if LeadQualityFilter.is_social_media_link(real_url):
                continue
            if LeadQualityFilter.is_platform_only_website(real_url):
                continue

            # Make sure the result title / snippet actually looks like it is
            # about THIS business, not a random match.
            title = ""
            if link_el:
                title = (link_el.get_text(strip=True) or "").lower()
            snippet_el = el.select_one(".result__snippet") or el.select_one(".result__snippet")
            if snippet_el:
                title += " " + snippet_el.get_text(strip=True).lower()

            # Require at least one significant token from the business name
            # to appear in the title/snippet.
            if name_tokens and not any(t in title for t in name_tokens):
                logger.debug(
                    "Skipping result for '%s' — title does not match: %s",
                    business_name,
                    real_url,
                )
                continue

            if LeadQualityFilter.is_real_business_website(real_url):
                logger.info(
                    "Verifier found real website for '%s' in %s: %s",
                    business_name,
                    city,
                    real_url,
                )
                return {
                    "has_real_website": True,
                    "found_url": real_url,
                    "source": "duckduckgo",
                }

        logger.debug("No real website found for '%s' in %s", business_name, city)
        return {
            "has_real_website": False,
            "found_url": None,
            "source": "duckduckgo",
        }

    @staticmethod
    def _extract_real_url(href: str) -> str | None:
        """DuckDuckGo wraps external URLs in ``/l/?uddg=…`` redirects.
        Unwrap them so we can inspect the real domain.
        """
        if "duckduckgo.com" in href and "uddg=" in href:
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            if "uddg" in qs:
                return urllib.parse.unquote(qs["uddg"][0])
        return href
