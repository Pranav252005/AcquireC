"""Hardcoded lead quality filters to exclude malls, chains, and platform pages."""

from __future__ import annotations

import re

# Name patterns that indicate malls, shopping centres, or large irrelevant venues
BLOCKED_NAME_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bmall\b", re.I),
    re.compile(r"\bshopping\s+(centre|center|mall|complex)\b", re.I),
    re.compile(r"\bplaza\b", re.I),
    re.compile(r"\bhyp(er)?\s*market\b", re.I),
    re.compile(r"\bsuperstore\b", re.I),
    re.compile(r"\bwarehouse\b", re.I),
    re.compile(r"\bfactory\s+outlet\b", re.I),
    re.compile(r"\bretail\s+india\b", re.I),  # generic aggregators
    re.compile(r"\bbrand\s+warehouse\b", re.I),
    re.compile(r"\bapple\s+premium\s+reseller\b", re.I),
    re.compile(r"\b(reliance|jio|big\s+bazaar|dmart|walmart|tesco|carrefour)\b", re.I),
    # Common Indian / international mall chains
    re.compile(r"\bvr\s+(surat|ahmedabad|bengaluru|bangalore|chennai|hyderabad|mumbai|delhi|pune|kolkata)\b", re.I),
    re.compile(r"\b(pvr|forum|lulu|phoenix|ambience|dlf|select\s+citywalk|elan|mgf| Vegas)\b", re.I),
]

# If category is "retail", also block these sub-types that Google Maps returns
RETAIL_SUBTYPE_BLOCKLIST: list[re.Pattern] = [
    re.compile(r"\bmall\b", re.I),
    re.compile(r"\bshopping\s+mall\b", re.I),
]


class LeadQualityFilter:
    """Filter out low-quality or irrelevant leads post-discovery."""

    @staticmethod
    def is_blocked_name(name: str, category: str = "") -> bool:
        """Return True if the business name matches blocked patterns."""
        if any(p.search(name) for p in BLOCKED_NAME_PATTERNS):
            return True
        if category.lower() == "retail":
            if any(p.search(name) for p in RETAIL_SUBTYPE_BLOCKLIST):
                return True
        return False

    @staticmethod
    def is_platform_only_website(url: str | None) -> bool:
        """Return True if the URL is a third-party platform page, not a real website."""
        if not url:
            return False
        platform_hosts = [
            "swiggy.com",
            "zomato.com",
            "link.zomato.com",
            "grexa.site",
            "bytecard.in",
            "vercel.app",
            "wixsite.com",
            "wixstudio.com",
        ]
        return any(h in url.lower() for h in platform_hosts)
