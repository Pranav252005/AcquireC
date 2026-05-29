"""Tests for lead quality filters."""

import pytest

from src.filters import LeadQualityFilter


@pytest.mark.parametrize(
    "name,expected",
    [
        ("VR Surat", True),
        ("Phoenix Mall Of Asia", True),
        ("Reliance SMART Superstore", True),
        ("iMagine Apple Premium Reseller", True),
        ("KPN Fresh", False),
        ("Delhi Fashion Boutique", False),
        ("Allure unisex salon", False),
        ("Ds Hair salon", False),
        ("Retail India", True),
        ("Brand Warehouse", True),
        ("Inorbit Mall Vadodara", True),
        ("Nexus Ahmedabad One", False),  # "nexus" is not in blocklist
    ],
)
def test_blocked_names(name, expected):
    assert LeadQualityFilter.is_blocked_name(name, "retail") == expected


def test_retail_subtypes():
    assert LeadQualityFilter.is_blocked_name("Some Mall", "retail")
    assert LeadQualityFilter.is_blocked_name("Some Mall", "cafe")  # malls blocked everywhere
    assert not LeadQualityFilter.is_blocked_name("Nice Shop", "retail")


def test_platform_urls():
    assert LeadQualityFilter.is_platform_only_website(
        "https://www.swiggy.com/restaurants/foo"
    )
    assert LeadQualityFilter.is_platform_only_website("https://link.zomato.com/xqzv")
    assert not LeadQualityFilter.is_platform_only_website("https://kpnfresh.com/")
    assert not LeadQualityFilter.is_platform_only_website(None)


def test_social_media_links():
    assert LeadQualityFilter.is_social_media_link("https://instagram.com/kgcafe")
    assert LeadQualityFilter.is_social_media_link("https://www.linkedin.com/company/foo")
    assert LeadQualityFilter.is_social_media_link("https://facebook.com/pages/bar")
    assert LeadQualityFilter.is_social_media_link("https://x.com/baz")
    assert LeadQualityFilter.is_social_media_link("https://youtube.com/channel/xyz")
    assert LeadQualityFilter.is_social_media_link("https://linktr.ee/mycafe")
    assert not LeadQualityFilter.is_social_media_link("https://kpnfresh.com/")
    assert not LeadQualityFilter.is_social_media_link(None)


def test_real_business_website():
    assert LeadQualityFilter.is_real_business_website("https://kgcafe.in")
    assert LeadQualityFilter.is_real_business_website("http://www.zencafe.co")
    assert LeadQualityFilter.is_real_business_website("https://example.com/path")
    # Social media and platforms are NOT real business websites
    assert not LeadQualityFilter.is_real_business_website("https://instagram.com/kgcafe")
    assert not LeadQualityFilter.is_real_business_website("https://swiggy.com/restaurants/foo")
    assert not LeadQualityFilter.is_real_business_website(None)


def test_classify_website():
    assert LeadQualityFilter.classify_website("https://kgcafe.in") == "real_website"
    assert LeadQualityFilter.classify_website("http://www.zencafe.co") == "real_website"
    assert LeadQualityFilter.classify_website("https://instagram.com/kgcafe") == "social_media"
    assert LeadQualityFilter.classify_website("https://linkedin.com/company/foo") == "social_media"
    assert LeadQualityFilter.classify_website("https://swiggy.com/restaurants/foo") == "platform_page"
    assert LeadQualityFilter.classify_website("https://link.zomato.com/xqzv") == "platform_page"
    assert LeadQualityFilter.classify_website(None) is None
    assert LeadQualityFilter.classify_website("") is None


@pytest.mark.parametrize(
    "name,city,expected",
    [
        ("Mumbai shops", "Mumbai", True),
        ("Mumbai Shops", "Mumbai", True),
        ("Thrift store in Mumbai", "Mumbai", True),
        ("Best cafe in Bandra", "Bandra", True),
        ("Cafe in Mumbai", "Mumbai", True),
        ("Restaurants in Delhi", "Delhi", True),
        ("Sharma Sweets", "Mumbai", False),
        ("Mumbai Biryani House", "Mumbai", False),
        ("The Blue Door Cafe", "Mumbai", False),
        ("KPN Fresh", "Delhi", False),
        ("Near me salon", "Mumbai", True),
        ("Mumbai thrift store", "Mumbai", True),
        ("Mumbai fashion store", "Mumbai", True),
    ],
)
def test_generic_names(name, city, expected):
    assert LeadQualityFilter.is_generic_name(name, city) == expected
