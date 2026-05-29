"""Business intelligence framework: maturity analysis, report cards, and benefit mapping."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BusinessReportCard:
    """Comprehensive analysis of a business's digital maturity and opportunities."""

    business_name: str
    maturity_stage: str
    digital_readiness: int
    biggest_pain_point: str
    competitor_gap: str
    estimated_revenue_tier: str
    recommended_strategy: str
    projected_roi_months: int
    website_benefit_lines: list[str]
    membership_concept_summary: str


class MaturityAnalyzer:
    """Analyze business maturity based on years in operation and digital signals."""

    STAGES = ["startup", "growth", "established", "legacy"]

    @staticmethod
    def infer_stage(years_in_business: int | None) -> str:
        """Map years to maturity stage."""
        if years_in_business is None:
            return "unknown"
        if years_in_business <= 1:
            return "startup"
        if years_in_business <= 5:
            return "growth"
        if years_in_business <= 15:
            return "established"
        return "legacy"

    @staticmethod
    def infer_digital_readiness(
        has_website: bool,
        website_score: str,
        review_count: int | None,
        detected_cms: str | None,
    ) -> int:
        """Score digital readiness 1-10."""
        score = 5
        if not has_website:
            score -= 3
        if website_score == "good":
            score += 2
        elif website_score == "poor":
            score -= 2
        if review_count and review_count > 100:
            score += 1
        if detected_cms in ("wix", "squarespace", "wordpress"):
            score += 1  # DIY builder = ready to upgrade
        return max(1, min(10, score))

    @staticmethod
    def get_website_benefits(maturity_stage: str, business_type: str) -> list[str]:
        """Return specific website benefits for a maturity stage."""
        benefits = {
            "startup": [
                "Your website is your 24/7 storefront before word-of-mouth kicks in",
                "Collect customer emails from day one — your most valuable asset",
                "Google Business Profile + website = you show up when someone searches nearby",
                "One professional page builds more trust than 50 social media posts",
                "Local SEO puts you on the map before bigger chains notice the neighborhood",
                "A simple booking link turns Instagram likes into actual appointments",
            ],
            "growth": [
                "You're losing bookings to competitors with online reservation systems",
                "Your staff spends 30+ mins/day answering 'are you open?' — a website answers it instantly",
                "Every social media follower should click to your menu/services in 1 tap",
                "Online reviews on your own site = you control the narrative",
                "Peak-hour demand is wasted without online pre-orders or reservations",
                "Your repeat customers want to refer friends — give them a link to share",
            ],
            "established": [
                "You've built the reputation — now let the website work while you sleep",
                "Your regulars are aging; their kids search on Google, not memory",
                "A loyalty program integrated into your site increases visit frequency by 20-30%",
                "Online pre-orders for peak hours = smoother operations + higher ticket size",
                "Data from your site shows which services are trending — no more guessing",
                "Former customers who moved away can still buy gift cards or merch online",
            ],
            "legacy": [
                "Your competitors are retiring too — the ones with websites are selling to younger owners",
                "Your staff can learn one simple system — we train them personally",
                "Keep your phone number, keep your routines, just add a digital front door",
                "When you decide to sell, a business with a website sells for 20-40% more",
                "Grandchildren of your loyal customers search online — meet them where they are",
                "A photo gallery of your history and craftsmanship builds instant credibility",
            ],
        }
        base = benefits.get(maturity_stage, benefits["growth"])

        # Add business-type-specific benefits
        type_addons: dict[str, list[str]] = {
            "cafe": [
                "Instagram-integrated gallery drives foot traffic from foodies",
                "Online menu with photos reduces 'what do you serve?' questions",
                "Laptop-friendly seating reservations for remote workers",
            ],
            "restaurant": [
                "Reservation system fills tables during slow Tuesday lunches",
                "Digital menu with dietary filters reduces waitstaff interruptions",
                "Pre-order for peak hours = kitchen runs smoother + bigger tickets",
            ],
            "salon": [
                "Online booking reduces no-shows by 40% with SMS reminders",
                "Stylist portfolios let clients choose who cuts their hair",
                "Product shop turns one-time visitors into recurring buyers",
            ],
            "spa": [
                "Package upsells on the website increase average ticket by 25%",
                "Therapist preference booking builds client loyalty",
                "Gift cards sold online bring new customers during slow months",
            ],
            "retail": [
                "E-commerce readiness turns walk-ins into online repeat buyers",
                "Back-in-stock alerts recover sales that would have gone to competitors",
                "Member-only drops create urgency and social proof",
            ],
            "clinic": [
                "Patient portal reduces front-desk call volume by 60%",
                "Online forms mean patients arrive with paperwork already done",
                "Appointment reminders via WhatsApp cut missed visits in half",
            ],
            "doctor": [
                "Online forms mean patients arrive with paperwork already done",
                "Telemedicine scheduling expands your reach beyond the neighborhood",
                "Health articles on your site position you as the local expert",
            ],
            "gym": [
                "Class booking with waitlists means no empty spots go wasted",
                "Progress dashboards keep members motivated and retained longer",
                "Nutrition plan portal adds a second revenue stream",
            ],
            "tuition": [
                "Recorded class library lets students revise at their own pace",
                "Parent dashboards reduce 'how is my child doing?' calls",
                "Online test series attract students from outside your immediate area",
            ],
            "coaching": [
                "Client portal with milestone tracking improves retention 2x",
                "Resource library (worksheets, videos) adds passive income",
                "Group challenge leaderboards build community and referrals",
            ],
        }

        addon = type_addons.get(business_type.lower(), [])
        return base + addon

    @staticmethod
    def infer_biggest_pain_point(
        maturity_stage: str,
        has_website: bool,
        website_score: str,
        business_type: str,
    ) -> str:
        """Infer the single biggest pain point for outreach targeting."""
        if not has_website:
            if maturity_stage == "startup":
                return "Completely invisible to online searchers; relying only on foot traffic and referrals"
            if maturity_stage == "legacy":
                return "Decades of reputation trapped offline; younger customers can't find them"
            return "No digital presence means losing customers to competitors who show up on Google"

        if website_score == "poor":
            if maturity_stage in ("established", "legacy"):
                return "Outdated website damages credibility; customers question if they're still open"
            return "Slow, broken website drives mobile visitors away before they see offerings"

        if maturity_stage == "growth":
            return "DIY website has hit its limit; can't handle bookings, payments, or growth"

        if maturity_stage == "established":
            return "No automation means owner is still answering every inquiry personally"

        return "Missing online booking and loyalty systems that competitors already have"

    @staticmethod
    def infer_revenue_tier(price_level: str | None, review_count: int | None) -> str:
        """Estimate monthly revenue tier from signals."""
        if price_level == "$$$$":
            return "high"
        if price_level == "$$$":
            return "medium-high"
        if price_level == "$$" and (review_count or 0) > 100:
            return "medium"
        if price_level == "$":
            return "low"
        if review_count and review_count > 200:
            return "medium"
        return "unknown"

    @staticmethod
    def recommend_strategy(maturity_stage: str, digital_readiness: int) -> str:
        """Recommend approach based on maturity and readiness."""
        if maturity_stage == "startup":
            return "landing_page_plus_google"
        if maturity_stage == "legacy" and digital_readiness < 4:
            return "gradual_modernization"
        if digital_readiness < 5:
            return "website_plus_seo"
        if digital_readiness < 8:
            return "website_plus_booking_loyalty"
        return "full_digital_transformation"

    @classmethod
    def analyze(
        cls,
        business_name: str,
        business_type: str,
        years_in_business: int | None,
        has_website: bool,
        website_score: str,
        website_issues: list[str],
        review_count: int | None,
        price_level: str | None,
        detected_cms: str | None,
        membership_concept_summary: str = "",
    ) -> BusinessReportCard:
        """Generate a complete business report card."""
        stage = cls.infer_stage(years_in_business)
        readiness = cls.infer_digital_readiness(has_website, website_score, review_count, detected_cms)
        pain = cls.infer_biggest_pain_point(stage, has_website, website_score, business_type)
        revenue_tier = cls.infer_revenue_tier(price_level, review_count)
        strategy = cls.recommend_strategy(stage, readiness)
        benefits = cls.get_website_benefits(stage, business_type)

        # ROI estimate
        roi_map = {
            "startup": 4,
            "growth": 2,
            "established": 3,
            "legacy": 6,
        }
        roi = roi_map.get(stage, 3)
        if readiness < 4:
            roi += 1  # harder to convert

        # Competitor gap
        if not has_website:
            gap = "Competitors with websites capture 70%+ of 'near me' search traffic"
        elif website_score == "poor":
            gap = "Competitors with modern sites look more trustworthy and professional"
        elif stage == "established":
            gap = "Newer competitors are stealing younger customers with Instagram-friendly sites and online booking"
        else:
            gap = "Competitors may have loyalty programs and member apps that build retention"

        return BusinessReportCard(
            business_name=business_name,
            maturity_stage=stage,
            digital_readiness=readiness,
            biggest_pain_point=pain,
            competitor_gap=gap,
            estimated_revenue_tier=revenue_tier,
            recommended_strategy=strategy,
            projected_roi_months=roi,
            website_benefit_lines=benefits,
            membership_concept_summary=membership_concept_summary,
        )


class LeadScorer:
    """Score leads 1-100 based on maturity, engagement, and opportunity."""

    @classmethod
    def score(
        cls,
        years_in_business: int | None,
        has_website: bool,
        website_score: str,
        review_count: int | None,
        rating: float | None,
        reply_intent: str | None = None,
    ) -> int:
        """Calculate lead score."""
        score = 50

        # Maturity bonus
        if years_in_business is not None:
            if 3 <= years_in_business <= 10:
                score += 15  # sweet spot: established but hungry
            elif years_in_business > 15:
                score += 5  # legacy, harder to convert but high value
            elif years_in_business < 2:
                score += 10  # startup, needs help but budget-limited

        # Website gap = opportunity
        if not has_website:
            score += 20
        elif website_score == "poor":
            score += 15
        elif website_score == "needs_work":
            score += 10

        # Social proof
        if review_count and review_count > 50:
            score += 5
        if review_count and review_count > 200:
            score += 5

        # Rating quality
        if rating and rating >= 4.5:
            score += 5
        elif rating and rating < 3.5:
            score -= 10  # struggling business, may not invest

        # Engagement
        if reply_intent == "interested":
            score += 20
        elif reply_intent == "price_inquiry":
            score += 15
        elif reply_intent == "booked":
            score += 25
        elif reply_intent == "not_interested":
            score = max(0, score - 60)

        return max(0, min(100, score))
