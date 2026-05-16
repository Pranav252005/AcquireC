"""Tests for business intelligence module."""

import pytest

from src.business_intelligence import BusinessReportCard, LeadScorer, MaturityAnalyzer


class TestMaturityAnalyzer:
    def test_infer_stage_startup(self) -> None:
        assert MaturityAnalyzer.infer_stage(0) == "startup"
        assert MaturityAnalyzer.infer_stage(1) == "startup"

    def test_infer_stage_growth(self) -> None:
        assert MaturityAnalyzer.infer_stage(2) == "growth"
        assert MaturityAnalyzer.infer_stage(5) == "growth"

    def test_infer_stage_established(self) -> None:
        assert MaturityAnalyzer.infer_stage(6) == "established"
        assert MaturityAnalyzer.infer_stage(15) == "established"

    def test_infer_stage_legacy(self) -> None:
        assert MaturityAnalyzer.infer_stage(16) == "legacy"
        assert MaturityAnalyzer.infer_stage(50) == "legacy"

    def test_infer_stage_none(self) -> None:
        assert MaturityAnalyzer.infer_stage(None) == "unknown"

    def test_digital_readiness_no_website(self) -> None:
        score = MaturityAnalyzer.infer_digital_readiness(
            has_website=False, website_score="none", review_count=None, detected_cms=None
        )
        assert score < 5

    def test_digital_readiness_good_website(self) -> None:
        score = MaturityAnalyzer.infer_digital_readiness(
            has_website=True, website_score="good", review_count=200, detected_cms="wordpress"
        )
        assert score >= 7

    def test_recommend_strategy_startup(self) -> None:
        assert MaturityAnalyzer.recommend_strategy("startup", 3) == "landing_page_plus_google"

    def test_recommend_strategy_legacy_low_readiness(self) -> None:
        assert MaturityAnalyzer.recommend_strategy("legacy", 3) == "gradual_modernization"

    def test_analyze_returns_report_card(self) -> None:
        report = MaturityAnalyzer.analyze(
            business_name="Test Cafe",
            business_type="cafe",
            years_in_business=8,
            has_website=False,
            website_score="none",
            website_issues=[],
            review_count=120,
            price_level="$$",
            detected_cms=None,
        )
        assert isinstance(report, BusinessReportCard)
        assert report.maturity_stage == "established"
        assert report.business_name == "Test Cafe"
        assert report.digital_readiness is not None
        assert report.biggest_pain_point != ""
        assert report.projected_roi_months > 0


class TestLeadScorer:
    def test_score_base(self) -> None:
        score = LeadScorer.score(
            years_in_business=5, has_website=False, website_score="none",
            review_count=None, rating=None
        )
        assert 50 <= score <= 100

    def test_score_no_website_gets_bonus(self) -> None:
        with_website = LeadScorer.score(
            years_in_business=5, has_website=True, website_score="good",
            review_count=None, rating=None
        )
        without_website = LeadScorer.score(
            years_in_business=5, has_website=False, website_score="none",
            review_count=None, rating=None
        )
        assert without_website > with_website

    def test_score_interested_reply(self) -> None:
        score = LeadScorer.score(
            years_in_business=5, has_website=False, website_score="none",
            review_count=None, rating=None, reply_intent="interested"
        )
        assert score >= 70

    def test_score_not_interested_penalty(self) -> None:
        score = LeadScorer.score(
            years_in_business=5, has_website=False, website_score="none",
            review_count=None, rating=None, reply_intent="not_interested"
        )
        assert score <= 30

    def test_score_bounds(self) -> None:
        assert LeadScorer.score(None, False, "none", None, None) >= 0
        assert LeadScorer.score(None, False, "none", None, None) <= 100
