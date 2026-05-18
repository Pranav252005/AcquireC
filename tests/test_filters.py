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
