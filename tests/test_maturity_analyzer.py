"""Additional tests for MaturityAnalyzer edge cases."""

from src.business_intelligence import MaturityAnalyzer


class TestMaturityAnalyzerKnownOutputs:
    """Test MaturityAnalyzer.analyze with known inputs/outputs."""

    def test_startup_no_website(self) -> None:
        """A new business without a website should be startup stage with low digital readiness."""
        report = MaturityAnalyzer.analyze(
            business_name="New Cafe",
            business_type="cafe",
            years_in_business=1,
            has_website=False,
            website_score="none",
            website_issues=[],
            review_count=0,
            price_level=None,
            detected_cms=None,
        )
        assert report.maturity_stage == "startup"
        assert report.digital_readiness <= 3
        assert any(word in report.biggest_pain_point.lower() for word in ["online", "website", "invisible", "search"])

    def test_established_with_good_website(self) -> None:
        """An old business with a good website should be established."""
        report = MaturityAnalyzer.analyze(
            business_name="Old Hotel",
            business_type="hotel",
            years_in_business=15,
            has_website=True,
            website_score="good",
            website_issues=[],
            review_count=100,
            price_level="$$",
            detected_cms="wordpress",
        )
        assert report.maturity_stage == "established"
        assert report.digital_readiness >= 7

    def test_legacy_with_poor_website(self) -> None:
        """An old business with a poor website should be legacy."""
        report = MaturityAnalyzer.analyze(
            business_name="Legacy Shop",
            business_type="retail",
            years_in_business=20,
            has_website=True,
            website_score="poor",
            website_issues=["missing_viewport_meta", "deprecated_tag_font"],
            review_count=10,
            price_level="$",
            detected_cms=None,
        )
        assert report.maturity_stage == "legacy"
        assert report.digital_readiness <= 4

    def test_growth_stage_mid_life(self) -> None:
        """A 5-year-old business with needs_work website should be growth."""
        report = MaturityAnalyzer.analyze(
            business_name="Growing Gym",
            business_type="gym",
            years_in_business=5,
            has_website=True,
            website_score="needs_work",
            website_issues=["slow_load_6000ms"],
            review_count=25,
            price_level="$$",
            detected_cms=None,
        )
        assert report.maturity_stage == "growth"


class TestLeadScorerEdgeCases:
    """Test LeadScorer edge cases."""

    def test_none_years_defaults_to_zero(self) -> None:
        """None years should not crash and should score reasonably."""
        from src.business_intelligence import LeadScorer
        score = LeadScorer.score(
            years_in_business=None,
            has_website=False,
            website_score="none",
            review_count=0,
            rating=None,
        )
        assert 0 <= score <= 100

    def test_no_website_gets_bonus(self) -> None:
        """Businesses without websites should get a higher score (more need)."""
        from src.business_intelligence import LeadScorer
        score_no_site = LeadScorer.score(
            years_in_business=5,
            has_website=False,
            website_score="none",
            review_count=10,
            rating=4.0,
        )
        score_good_site = LeadScorer.score(
            years_in_business=5,
            has_website=True,
            website_score="good",
            review_count=10,
            rating=4.0,
        )
        assert score_no_site > score_good_site

    def test_high_reviews_boost_score(self) -> None:
        """Many reviews should increase the score."""
        from src.business_intelligence import LeadScorer
        score_low = LeadScorer.score(
            years_in_business=5,
            has_website=True,
            website_score="needs_work",
            review_count=5,
            rating=3.5,
        )
        score_high = LeadScorer.score(
            years_in_business=5,
            has_website=True,
            website_score="needs_work",
            review_count=500,
            rating=4.8,
        )
        assert score_high > score_low

    def test_score_bounds(self) -> None:
        """Score should always be between 0 and 100."""
        from src.business_intelligence import LeadScorer
        score = LeadScorer.score(
            years_in_business=50,
            has_website=True,
            website_score="poor",
            review_count=10000,
            rating=5.0,
        )
        assert 0 <= score <= 100
