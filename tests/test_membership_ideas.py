"""Tests for membership ideas module."""

import pytest

from src.membership_ideas import MembershipConcept, MembershipLibrary


class TestMembershipLibrary:
    def test_get_concept_cafe(self) -> None:
        concept = MembershipLibrary.get_concept("cafe")
        assert concept is not None
        assert concept.name == "The Regulars Club"
        assert len(concept.tiers) == 3

    def test_get_concept_restaurant(self) -> None:
        concept = MembershipLibrary.get_concept("restaurant")
        assert concept is not None
        assert concept.name == "Chef's Table Circle"

    def test_get_concept_salon(self) -> None:
        concept = MembershipLibrary.get_concept("salon")
        assert concept is not None
        assert concept.name == "Glow Pass"

    def test_get_concept_clinic(self) -> None:
        concept = MembershipLibrary.get_concept("clinic")
        assert concept is not None
        assert concept.name == "Family Health Plan"

    def test_get_concept_unknown_returns_none(self) -> None:
        assert MembershipLibrary.get_concept("unknown_type") is None

    def test_format_for_pitch_includes_tiers(self) -> None:
        text = MembershipLibrary.format_for_pitch("cafe", currency="inr")
        assert "Espresso" in text
        assert "₹299" in text
        assert "Regulars Club" in text

    def test_format_for_pitch_usd(self) -> None:
        text = MembershipLibrary.format_for_pitch("cafe", currency="usd")
        assert "$4" in text

    def test_all_concepts_have_required_fields(self) -> None:
        for btype in ["cafe", "restaurant", "salon", "retail", "clinic", "gym", "tuition"]:
            concept = MembershipLibrary.get_concept(btype)
            assert concept is not None, f"Missing concept for {btype}"
            assert concept.name
            assert concept.description
            assert len(concept.tiers) == 3
            assert concept.pitch_hook
            assert concept.revenue_example
