"""Tests for city_rotator module."""

import pytest

from src.core.city_rotator import CITY_TIERS, CityRotator


class TestCityRotator:
    """Test suite for CityRotator."""

    def test_builds_queue_from_preset_cities(self) -> None:
        """CityRotator should build queue from preset cities."""
        preset = {"target": {"cities": ["Mumbai", "Delhi"]}}
        rotator = CityRotator(target_count=10, preset=preset)
        assert rotator.city_queue == ["Mumbai", "Delhi"]

    def test_builds_default_queue_when_preset_is_auto_rotate(self) -> None:
        """CityRotator should build default queue when preset is auto_rotate."""
        preset = {"target": {"cities": ["auto_rotate"]}}
        rotator = CityRotator(target_count=10, preset=preset)
        expected = []
        for tier in ["tier_1_india", "tier_2_india", "tier_3_india", "tier_1_global"]:
            expected.extend(CITY_TIERS.get(tier, []))
        assert rotator.city_queue == expected

    def test_get_next_city_returns_cities_in_order(self) -> None:
        """get_next_city should return cities in queue order."""
        preset = {"target": {"cities": ["Mumbai", "Delhi", "Bangalore"]}}
        rotator = CityRotator(target_count=10, preset=preset)
        assert rotator.get_next_city() == "Mumbai"
        rotator.mark_exhausted("Mumbai", found_count=3)
        assert rotator.get_next_city() == "Delhi"
        rotator.mark_exhausted("Delhi", found_count=3)
        assert rotator.get_next_city() == "Bangalore"

    def test_mark_exhausted_adds_city_to_exhausted_set(self) -> None:
        """mark_exhausted should add city to exhausted set when found_count < 5."""
        rotator = CityRotator(target_count=10)
        rotator.mark_exhausted("Mumbai", found_count=3)
        assert "Mumbai" in rotator.exhausted_cities

    def test_mark_exhausted_does_not_add_city_when_found_count_is_five_or_more(self) -> None:
        """mark_exhausted should not add city to exhausted set when found_count >= 5."""
        rotator = CityRotator(target_count=10)
        rotator.mark_exhausted("Mumbai", found_count=5)
        assert "Mumbai" not in rotator.exhausted_cities

    def test_is_complete_returns_true_when_target_reached(self) -> None:
        """is_complete should return True when found >= target."""
        rotator = CityRotator(target_count=10)
        rotator.mark_exhausted("Mumbai", found_count=10)
        assert rotator.is_complete() is True

    def test_is_complete_returns_false_when_under_target(self) -> None:
        """is_complete should return False when found < target."""
        rotator = CityRotator(target_count=10)
        rotator.mark_exhausted("Mumbai", found_count=3)
        assert rotator.is_complete() is False

    def test_get_next_city_returns_none_when_all_exhausted(self) -> None:
        """get_next_city should return None when all cities are exhausted."""
        preset = {"target": {"cities": ["Mumbai"]}}
        rotator = CityRotator(target_count=10, preset=preset)
        rotator.mark_exhausted("Mumbai", found_count=3)
        assert rotator.get_next_city() is None
