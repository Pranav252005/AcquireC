"""Additional tests for PitchValidator edge cases."""

from src.ai_engine import PitchValidator


class TestPitchValidatorGoodBad:
    """Test PitchValidator with good and bad pitches."""

    def test_good_pitch_passes(self) -> None:
        """A well-formed pitch should pass validation with no errors."""
        validator = PitchValidator()
        good = {
            "pitch_text": (
                "Hi there, I came across your business and noticed you could benefit from a "
                "modern, mobile-friendly website that helps customers find you, learn what you offer, "
                "and get in touch easily. I build fast, beautiful websites tailored for local businesses. "
                "Would you be open to a quick chat about how a new site could drive more customers your way?"
            ),
            "context_summary": "Local business website pitch focusing on mobile experience",
            "membership_idea": "Regulars Club with 3 tiers generating predictable monthly revenue",
            "website_benefits": "Online booking, menu display, and contact form integration",
        }
        errors = validator.validate(good)
        assert errors == []

    def test_too_short_pitch_fails(self) -> None:
        """A pitch under 100 characters should fail."""
        validator = PitchValidator()
        bad = {
            "pitch_text": "Hi, we make websites. Call us.",
            "context_summary": "Too short",
            "membership_idea": "Too short",
            "website_benefits": "Too short",
        }
        errors = validator.validate(bad)
        assert any("too short" in e.lower() for e in errors)

    def test_missing_website_reference_fails(self) -> None:
        """A pitch without 'website' or 'site' should fail."""
        validator = PitchValidator()
        bad = {
            "pitch_text": (
                "Hi there, I came across your business and noticed you could benefit from "
                "a modern, mobile-friendly online presence that helps customers find you. "
                "I build fast, beautiful pages tailored for local businesses."
            ),
            "context_summary": "Pitch missing website keyword",
            "membership_idea": "Regulars Club with 3 tiers generating predictable monthly revenue",
            "website_benefits": "Online booking, menu display, and contact form integration",
        }
        errors = validator.validate(bad)
        assert any("missing website/site reference" in e.lower() for e in errors)

    def test_excessively_long_pitch_fails(self) -> None:
        """A pitch over 1200 characters should fail."""
        validator = PitchValidator()
        bad = {
            "pitch_text": "A" * 1300,
            "context_summary": "A" * 400,
            "membership_idea": "A" * 700,
            "website_benefits": "A" * 700,
        }
        errors = validator.validate(bad)
        assert any("too long" in e.lower() for e in errors)

    def test_empty_membership_idea_fails(self) -> None:
        """An empty membership_idea should fail the min_length check."""
        validator = PitchValidator()
        bad = {
            "pitch_text": (
                "Hi there, I came across your business and noticed you could benefit from a "
                "modern, mobile-friendly website that helps customers find you, learn what you offer, "
                "and get in touch easily. I build fast, beautiful websites tailored for local businesses. "
                "Would you be open to a quick chat about how a new site could drive more customers your way?"
            ),
            "context_summary": "Local business website pitch focusing on mobile experience",
            "membership_idea": "",
            "website_benefits": "Online booking, menu display, and contact form integration",
        }
        errors = validator.validate(bad)
        assert any("membership_idea too short" in e.lower() for e in errors)
