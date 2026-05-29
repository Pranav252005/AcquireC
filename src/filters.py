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

# Social media platforms — these are NOT real business websites
SOCIAL_MEDIA_HOSTS: list[str] = [
    "instagram.com",
    "facebook.com",
    "fb.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "tiktok.com",
    "pinterest.com",
    "threads.net",
    "snapchat.com",
    "reddit.com",
    "tumblr.com",
    "flickr.com",
    "whatsapp.com",
    "wa.me",
    "linktr.ee",
    "beacons.ai",
    "tap.bio",
    "lynk.id",
    "bio.link",
    "carrd.co",
]

# Third-party platform pages (not real business websites)
PLATFORM_HOSTS: list[str] = [
    # Food delivery & restaurant aggregators
    "swiggy.com",
    "zomato.com",
    "link.zomato.com",
    "ubereats.com",
    "doordash.com",
    "grubhub.com",
    "deliveroo.com",
    "foodpanda.com",
    "restaurant-guru.in",
    "dineout.co.in",
    "eazydiner.com",
    # Short-link / card platforms
    "grexa.site",
    "bytecard.in",
    # Website builders (free subdomains)
    "vercel.app",
    "wixsite.com",
    "wixstudio.com",
    "wix.com",
    # Indian business directories & aggregators
    "justdial.com",
    "indiamart.com",
    "sulekha.com",
    "practo.com",
    "magicpin.in",
    "nearbuy.com",
    "urbancompany.com",
    "yappe.in",
    "crowndevour.com",
    # Wedding / event directories
    "weddingwire.in",
    "wedmegood.com",
    "venuelook.com",
    # General directories & review sites
    "yelp.com",
    "tripadvisor.com",
    "tripadvisor.in",
    "foursquare.com",
    "yellowpages.com",
]

# Regex to detect a proper domain with a TLD
_DOMAIN_RE = re.compile(r"^(https?://)?(www\.)?[^/]+\.[a-z]{2,}", re.I)

# Generic business-name patterns that indicate a search-result placeholder,
# not a real business name.
GENERIC_NAME_PATTERNS: list[re.Pattern] = [
    # "Thrift store in Mumbai", "Best cafe in Bandra"
    re.compile(
        r"^(best\s+|top\s+)?(.+?)\s+in\s+(.+)$",
        re.I,
    ),
]

# Words that, when combined with a city name, form a generic listing rather
# than a real business name.
_GENERIC_CATEGORIES: set[str] = {
    "shop",
    "shops",
    "store",
    "stores",
    "cafe",
    "cafes",
    "restaurant",
    "restaurants",
    "salon",
    "salons",
    "hotel",
    "hotels",
    "clinic",
    "clinics",
    "boutique",
    "boutiques",
    "market",
    "markets",
    "mall",
    "malls",
    "thrift",
    "bakery",
    "bakeries",
    "bar",
    "bars",
    "pub",
    "pubs",
    "spa",
    "spas",
    "studio",
    "studios",
    "gym",
    "gyms",
    "center",
    "centre",
    "complex",
    "outlet",
    "showroom",
    "dealership",
}

# Generic suffixes that often follow a category word.
_GENERIC_SUFFIXES: set[str] = {
    "shop",
    "shops",
    "store",
    "stores",
    "center",
    "centre",
    "point",
    "corner",
}


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
        return any(h in url.lower() for h in PLATFORM_HOSTS)

    @staticmethod
    def is_social_media_link(url: str | None) -> bool:
        """Return True if the URL points to a social media / link-aggregator page."""
        if not url:
            return False
        return any(h in url.lower() for h in SOCIAL_MEDIA_HOSTS)

    @staticmethod
    def is_real_business_website(url: str | None) -> bool:
        """Return True if the URL looks like a proper business website domain.

        Social media links and platform pages are explicitly excluded.
        """
        if not url:
            return False
        if LeadQualityFilter.is_social_media_link(url):
            return False
        if LeadQualityFilter.is_platform_only_website(url):
            return False
        return bool(_DOMAIN_RE.match(url))

    @staticmethod
    def is_generic_name(name: str, city: str, category: str = "") -> bool:
        """Return True if *name* is a generic search-result placeholder.

        Examples of generic names that should be rejected:
            - "Mumbai shops"
            - "Thrift store in Mumbai"
            - "Best cafe in Bandra"

        A real business name like "Mumbai Biryani House" or "Sharma Sweets"
        will pass through.
        """
        lower_name = name.lower().strip()
        lower_city = city.lower().strip()

        # Contains "near me" — always generic
        if "near me" in lower_name:
            return True

        # Pattern: "[Category] in [City]"  (e.g. "Thrift store in Mumbai")
        if " in " in lower_name:
            before_in = lower_name.split(" in ", 1)[0].strip()
            after_in = lower_name.split(" in ", 1)[1].strip()

            # The "in" must refer to the city we are searching
            if lower_city in after_in:
                # Remove common adjectives
                cleaned = re.sub(r"\b(best|top|new|old|the|a|an)\b", "", before_in)
                cleaned = cleaned.strip()
                words = [w for w in cleaned.split() if w]

                # If the part before "in" is just 1-2 generic words, it's generic
                if len(words) <= 2 and all(w in _GENERIC_CATEGORIES for w in words):
                    return True
                # Also generic if it's just "thrift store" (2 words, both generic-ish)
                if len(words) == 2 and words[1] in _GENERIC_SUFFIXES:
                    return True

        # Pattern: "[City] [Category]" (exactly 2 words)
        words = lower_name.split()
        if len(words) == 2:
            first, second = words
            # First word matches city (or is a substring of it)
            if first == lower_city or lower_city.startswith(first) or first.startswith(lower_city):
                if second in _GENERIC_CATEGORIES:
                    return True

        # Pattern: "[City] [Something] [Suffix]" (3 words)
        # e.g. "Mumbai fashion store", "Mumbai thrift store", "Delhi electronics shop"
        if len(words) == 3:
            first, second, third = words
            if first == lower_city or lower_city.startswith(first) or first.startswith(lower_city):
                if third in _GENERIC_SUFFIXES:
                    return True

        return False

    @staticmethod
    def classify_website(url: str | None) -> str | None:
        """Classify a URL into one of:

        - ``"real_website"``  → proper business domain (.com, .in, etc.)
        - ``"social_media"``  → Instagram, LinkedIn, Facebook, etc.
        - ``"platform_page"`` → Swiggy, Zomato, Wixsite, etc.
        - ``None``            → no URL at all
        """
        if not url:
            return None
        if LeadQualityFilter.is_social_media_link(url):
            return "social_media"
        if LeadQualityFilter.is_platform_only_website(url):
            return "platform_page"
        if LeadQualityFilter.is_real_business_website(url):
            return "real_website"
        return "unknown"
