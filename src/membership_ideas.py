"""Membership and loyalty concept library tailored per business type.

Each concept includes tiered pricing, benefits, and the website integration needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MembershipConcept:
    """A complete membership/loyalty program concept."""

    name: str
    description: str
    tiers: list[dict[str, Any]]
    website_features: list[str]
    pitch_hook: str
    revenue_example: str


class MembershipLibrary:
    """Library of pre-built membership concepts per business category."""

    _CONCEPTS: dict[str, MembershipConcept] = {
        "cafe": MembershipConcept(
            name="The Regulars Club",
            description="Turn daily coffee drinkers into paying members with predictable monthly revenue",
            tiers=[
                {
                    "name": "Espresso",
                    "price_usd": 4,
                    "price_inr": 299,
                    "benefits": ["1 free coffee daily", "10% off food", "Priority seating"],
                },
                {
                    "name": "Barista",
                    "price_usd": 8,
                    "price_inr": 599,
                    "benefits": [
                        "Everything in Espresso",
                        "2 free pastries/week",
                        "1 free guest coffee/day",
                        "Reserved table for 2 hrs",
                    ],
                },
                {
                    "name": "Roaster",
                    "price_usd": 12,
                    "price_inr": 999,
                    "benefits": [
                        "Everything in Barista",
                        "Unlimited wifi lounge 4 hrs/day",
                        "Tasting event invites",
                        "Name on Founders Wall",
                    ],
                },
            ],
            website_features=[
                "Member login portal to track credits",
                "QR code scan at counter for instant verification",
                "WhatsApp bot for renewal reminders",
                "Admin dashboard: active members, MRR, popular time slots",
            ],
            pitch_hook="With just 50 Regulars Club members at the Espresso tier, you generate ₹14,950/month in predictable revenue — enough to cover rent for most cafés.",
            revenue_example="50 members × ₹299 = ₹14,950/month predictable revenue",
        ),
        "restaurant": MembershipConcept(
            name="Chef's Table Circle",
            description="Transform occasional diners into regulars with priority access and exclusive experiences",
            tiers=[
                {
                    "name": "Diner",
                    "price_usd": 9,
                    "price_inr": 699,
                    "benefits": [
                        "1 complimentary appetizer per visit",
                        "10% off bill",
                        "Skip-the-wait list",
                    ],
                },
                {
                    "name": "Gourmet",
                    "price_usd": 16,
                    "price_inr": 1299,
                    "benefits": [
                        "1 complimentary main course/month",
                        "15% off bill",
                        "Reserved table Fridays",
                        "Birthday surprise dish",
                    ],
                },
                {
                    "name": "Connoisseur",
                    "price_usd": 30,
                    "price_inr": 2499,
                    "benefits": [
                        "Tasting menu preview access",
                        "Chef meet-and-greet quarterly",
                        "20% off bill",
                        "Private dining priority",
                    ],
                },
            ],
            website_features=[
                "Reservation system with member-only time slots",
                "Pre-order for tasting events (limited seats = FOMO)",
                "Review collection with bonus credits",
                "Inventory-aware menu that hides 86'd items",
            ],
            pitch_hook="Your best customers come twice a month. Chef's Table Circle turns them into members who come weekly — because they've already paid.",
            revenue_example="40 members × ₹1,299 = ₹51,960/month + higher visit frequency",
        ),
        "salon": MembershipConcept(
            name="Glow Pass",
            description="Fill empty weekday slots and guarantee recurring revenue with beauty memberships",
            tiers=[
                {
                    "name": "Glow",
                    "price_usd": 10,
                    "price_inr": 799,
                    "benefits": [
                        "1 free basic service/month (facial/haircut)",
                        "15% off all services",
                    ],
                },
                {
                    "name": "Radiance",
                    "price_usd": 18,
                    "price_inr": 1499,
                    "benefits": [
                        "2 premium services/month",
                        "20% off products",
                        "Priority weekend booking",
                    ],
                },
                {
                    "name": "Platinum",
                    "price_usd": 35,
                    "price_inr": 2999,
                    "benefits": [
                        "Unlimited basic services",
                        "1 free premium/month",
                        "25% off products",
                        "Personal stylist chat",
                    ],
                },
            ],
            website_features=[
                "Online booking with member-only time slots",
                "Service credit tracker",
                "Product e-commerce with member discounts",
                "Before/after gallery (members consent to feature)",
            ],
            pitch_hook="Your busiest hours are weekends, but weekdays are empty. Glow Pass members get priority weekend slots — creating scarcity. Their 'free monthly service' brings them in on Tuesdays and Wednesdays.",
            revenue_example="30 members × ₹1,499 = ₹44,970/month + filled weekday slots",
        ),
        "spa": MembershipConcept(
            name="Serenity Circle",
            description="Wellness memberships for massage, aromatherapy, and holistic treatments with predictable monthly revenue",
            tiers=[
                {
                    "name": "Relax",
                    "price_usd": 12,
                    "price_inr": 999,
                    "benefits": [
                        "1 massage or aromatherapy session/month",
                        "10% off retail products",
                        "Priority weekday booking",
                    ],
                },
                {
                    "name": "Rejuvenate",
                    "price_usd": 22,
                    "price_inr": 1799,
                    "benefits": [
                        "2 wellness treatments/month",
                        "20% off retail products",
                        "Sauna/steam access",
                        "Priority weekend booking",
                    ],
                },
                {
                    "name": "Nirvana",
                    "price_usd": 40,
                    "price_inr": 3299,
                    "benefits": [
                        "Unlimited basic treatments",
                        "1 premium facial or body wrap/month",
                        "25% off products",
                        "Nutrition consultation quarterly",
                    ],
                },
            ],
            website_features=[
                "Online booking with therapist preference",
                "Treatment history and recommendations",
                "Retail shop with member discounts",
                "Wellness blog and self-care guides",
            ],
            pitch_hook="Your spa has quiet Tuesdays and Thursdays. Serenity Circle members book those slots first — turning empty rooms into predictable revenue while you retail more products.",
            revenue_example="25 members × ₹1,799 = ₹44,975/month + higher retail sales",
        ),
        "retail": MembershipConcept(
            name="Insider Circle",
            description="Create 'drop culture' with exclusive access and turn one-time buyers into repeat customers",
            tiers=[
                {
                    "name": "Insider",
                    "price_usd": 5,
                    "price_inr": 399,
                    "benefits": [
                        "Early access to new stock",
                        "10% off",
                        "Free delivery",
                    ],
                },
                {
                    "name": "VIP",
                    "price_usd": 11,
                    "price_inr": 899,
                    "benefits": [
                        "Everything in Insider",
                        "20% off",
                        "Personal shopper chat",
                        "Exclusive colorways",
                    ],
                },
                {
                    "name": "Founder",
                    "price_usd": 25,
                    "price_inr": 1999,
                    "benefits": [
                        "Everything in VIP",
                        "Quarterly surprise box",
                        "Name in store credits",
                        "Invite-only sales",
                    ],
                },
            ],
            website_features=[
                "Members-only product drops (password-protected catalog pages)",
                "Wishlist + back-in-stock alerts",
                "WhatsApp broadcast for insider drops",
                "Loyalty points tracker",
            ],
            pitch_hook="Right now, a customer buys once and forgets you. Insider Circle creates 'drop culture' — members check your site every Tuesday for new stock because they get first dibs.",
            revenue_example="60 members × ₹899 = ₹53,940/month + higher repeat purchase rate",
        ),
        "clinic": MembershipConcept(
            name="Family Health Plan",
            description="Convert walk-in patients into recurring revenue with preventive care memberships",
            tiers=[
                {
                    "name": "Individual",
                    "price_usd": 6,
                    "price_inr": 499,
                    "benefits": [
                        "1 free consultation/month",
                        "10% off diagnostics",
                        "24hr chat with nurse",
                    ],
                },
                {
                    "name": "Family (4)",
                    "price_usd": 16,
                    "price_inr": 1299,
                    "benefits": [
                        "4 consultations/month",
                        "15% off diagnostics",
                        "Priority appointment booking",
                        "Vaccination tracker",
                    ],
                },
                {
                    "name": "Senior Care",
                    "price_usd": 12,
                    "price_inr": 999,
                    "benefits": [
                        "2 home-visit eligible consults/month",
                        "Medicine reminders via WhatsApp",
                        "Emergency hotline",
                    ],
                },
            ],
            website_features=[
                "Patient portal with medical history",
                "Appointment booking with doctor preference",
                "WhatsApp reminder bot for medications and appointments",
                "Family account linking (parent manages kids + elderly parents)",
            ],
            pitch_hook="A family of four visiting twice a year generates ₹4,000. A Family Health Plan member pays ₹1,299/month = ₹15,588/year. That's 4x revenue per family.",
            revenue_example="20 families × ₹1,299 = ₹25,980/month predictable revenue",
        ),
        "doctor": MembershipConcept(
            name="Premier Care Plan",
            description="Private practice memberships for individual doctors offering preventive care and telemedicine",
            tiers=[
                {
                    "name": "Essential",
                    "price_usd": 8,
                    "price_inr": 699,
                    "benefits": [
                        "1 in-clinic consultation/month",
                        "Telemedicine chat support",
                        "10% off diagnostics",
                    ],
                },
                {
                    "name": "Preferred",
                    "price_usd": 18,
                    "price_inr": 1499,
                    "benefits": [
                        "3 consultations/month (clinic or video)",
                        "Second opinion service",
                        "15% off diagnostics",
                        "Priority same-day slots",
                    ],
                },
                {
                    "name": "Concierge",
                    "price_usd": 35,
                    "price_inr": 2999,
                    "benefits": [
                        "Unlimited consultations",
                        "Home visit eligibility",
                        "20% off diagnostics",
                        "Dedicated health manager",
                    ],
                },
            ],
            website_features=[
                "Patient portal with health records",
                "Telemedicine video booking",
                "Prescription refill requests",
                "Health tips newsletter subscription",
            ],
            pitch_hook="A patient who pays per visit comes when sick. A Premier Care member comes for preventive check-ups — 3x more visits per year and better health outcomes.",
            revenue_example="20 members × ₹1,499 = ₹29,980/month predictable revenue",
        ),
        "gym": MembershipConcept(
            name="Fit Squad",
            description="Go beyond basic gym membership with training credits and progress tracking",
            tiers=[
                {
                    "name": "Starter",
                    "price_usd": 12,
                    "price_inr": 999,
                    "benefits": [
                        "1 personal training session/month",
                        "Nutrition guide access",
                        "Class booking",
                    ],
                },
                {
                    "name": "Pro",
                    "price_usd": 24,
                    "price_inr": 1999,
                    "benefits": [
                        "4 PT sessions/month",
                        "Body composition tracking",
                        "Priority class booking",
                    ],
                },
                {
                    "name": "Elite",
                    "price_usd": 48,
                    "price_inr": 3999,
                    "benefits": [
                        "Unlimited PT",
                        "Recovery lounge access",
                        "Guest passes",
                        "Branded merchandise",
                    ],
                },
            ],
            website_features=[
                "Class schedule with real-time capacity",
                "Progress dashboard (weight, measurements, attendance streak)",
                "Diet plan portal",
                "Community forum (members only)",
            ],
            pitch_hook="Most gyms sell access. Fit Squad sells results. Members who track progress stay 3x longer than basic members.",
            revenue_example="40 members × ₹1,999 = ₹79,960/month + higher retention",
        ),
        "fitness": MembershipConcept(
            name="Bootcamp Collective",
            description="Class-based fitness memberships for bootcamps, HIIT, and yoga studios — community-driven results",
            tiers=[
                {
                    "name": "Starter",
                    "price_usd": 10,
                    "price_inr": 799,
                    "benefits": [
                        "4 group classes/month",
                        "Outdoor session access",
                        "Community challenge entry",
                    ],
                },
                {
                    "name": "Pro",
                    "price_usd": 20,
                    "price_inr": 1599,
                    "benefits": [
                        "Unlimited group classes",
                        "Nutrition workshop access",
                        "Priority booking for popular sessions",
                        "Monthly body composition scan",
                    ],
                },
                {
                    "name": "Elite",
                    "price_usd": 35,
                    "price_inr": 2799,
                    "benefits": [
                        "Everything in Pro",
                        "1 semi-private session/week",
                        "Retreat discounts",
                        "Branded merch kit",
                    ],
                },
            ],
            website_features=[
                "Live class schedule with booking",
                "Challenge leaderboard and progress tracking",
                "Nutrition log and meal plans",
                "Member community chat",
            ],
            pitch_hook="Drop-in students come once. Bootcamp Collective members come 3x a week because the community holds them accountable — and they've already paid.",
            revenue_example="35 members × ₹1,599 = ₹55,965/month + higher attendance",
        ),
        "tuition": MembershipConcept(
            name="Scholar's Path",
            description="Transform one-time enrollments into recurring education memberships",
            tiers=[
                {
                    "name": "Learner",
                    "price_usd": 10,
                    "price_inr": 799,
                    "benefits": [
                        "1 extra doubt session/week",
                        "Recorded class access",
                        "Practice tests",
                    ],
                },
                {
                    "name": "Achiever",
                    "price_usd": 18,
                    "price_inr": 1499,
                    "benefits": [
                        "Everything in Learner",
                        "1-on-1 monthly review",
                        "Study material library",
                        "Parent progress reports",
                    ],
                },
                {
                    "name": "Topper",
                    "price_usd": 30,
                    "price_inr": 2499,
                    "benefits": [
                        "Everything in Achiever",
                        "Daily mentorship check-in",
                        "Mock exam series",
                        "Career counseling",
                    ],
                },
            ],
            website_features=[
                "Student portal with video library",
                "Test scoring dashboard",
                "Parent login for progress tracking",
                "Automated report cards",
            ],
            pitch_hook="A student who pays monthly stays enrolled 2x longer than per-course students. Scholar's Path turns enrollment anxiety into steady, predictable revenue.",
            revenue_example="25 students × ₹1,499 = ₹37,475/month predictable revenue",
        ),
        "coaching": MembershipConcept(
            name="Mentor Circle",
            description="Life and career coaching memberships with structured milestone tracking and community accountability",
            tiers=[
                {
                    "name": "Explorer",
                    "price_usd": 15,
                    "price_inr": 1199,
                    "benefits": [
                        "1 group coaching session/week",
                        "Goal-setting worksheet access",
                        "Community forum membership",
                    ],
                },
                {
                    "name": "Navigator",
                    "price_usd": 30,
                    "price_inr": 2499,
                    "benefits": [
                        "Everything in Explorer",
                        "2 private 1-on-1 sessions/month",
                        "Personalized action plan",
                        "Weekly accountability check-ins",
                    ],
                },
                {
                    "name": "Champion",
                    "price_usd": 60,
                    "price_inr": 4999,
                    "benefits": [
                        "Everything in Navigator",
                        "Unlimited private sessions",
                        "Priority booking for workshops",
                        "Quarterly retreat access",
                        "1-on-1 messaging with coach",
                    ],
                },
            ],
            website_features=[
                "Client portal with goal tracker and milestone timeline",
                "Session booking with coach preference",
                "Progress dashboard with visual achievements",
                "Community chat and peer accountability groups",
                "Resource library (worksheets, templates, videos)",
            ],
            pitch_hook="Most coaching clients quit after 3 sessions because there's no structure. Mentor Circle members stay 8+ months because weekly check-ins and milestone tracking keep them accountable.",
            revenue_example="20 Navigator members × ₹2,499 = ₹49,980/month predictable revenue",
        ),
    }

    @classmethod
    def get_concept(cls, business_type: str) -> MembershipConcept | None:
        """Get membership concept for a business type."""
        return cls._CONCEPTS.get(business_type.lower())

    @classmethod
    def format_for_pitch(cls, business_type: str, currency: str = "inr") -> str:
        """Format a membership concept as text for prompt injection.

        The concept is presented as an EXAMPLE ONLY. The AI is instructed
        to create something completely unique for each business.
        """
        concept = cls.get_concept(business_type)
        if not concept:
            return ""

        lines = [
            f"Example concept name (DO NOT use this name): {concept.name}",
            f"Example description: {concept.description}",
            "",
            "Example tier structure (adapt pricing and benefits to THIS business):",
        ]
        for tier in concept.tiers:
            price = tier.get("price_inr") if currency == "inr" else tier.get("price_usd")
            symbol = "₹" if currency == "inr" else "$"
            benefits = ", ".join(tier["benefits"])
            lines.append(f"  - {tier['name']}: {symbol}{price}/month — {benefits}")
        lines.append("")
        lines.append(f"Example hook: {concept.pitch_hook}")
        lines.append(f"Example revenue math: {concept.revenue_example}")
        lines.append("")
        lines.append("INSTRUCTION: Create a COMPLETELY DIFFERENT concept for THIS business.")
        lines.append("Use their actual offerings, name, and city to make it unique.")
        return "\n".join(lines)
