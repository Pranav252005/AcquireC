"""Business research + AI pitch generation via the new AI Engine."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import Browser
from sqlalchemy.orm import Session

from src.ai_engine import AIPitchEngine, BusinessContext
from src.business_intelligence import BusinessReportCard, MaturityAnalyzer
from src.config import get_settings
from src.membership_ideas import MembershipLibrary
from src.models import Lead

logger = logging.getLogger(__name__)


class LinkedInResearcher:
    """Research a business via its website and generate a pitch via the AI Engine."""

    def __init__(self, headless: bool = True, browser: Browser | None = None) -> None:
        self.headless = headless
        self.browser = browser
        self.settings = get_settings()
        self.ai_engine = AIPitchEngine()

    def research(
        self,
        db: Session,
        lead: Lead,
        website_audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Research lead via website and return enriched data + pitch."""
        web_data = self._enrich_from_website(lead)

        # Build business context
        has_website = bool(lead.website)
        website_score = website_audit.get("overall_score", "none") if website_audit else "none"
        website_issues = website_audit.get("layout_issues", []) + website_audit.get("old_tech_detected", []) if website_audit else []

        # Generate report card
        report = MaturityAnalyzer.analyze(
            business_name=lead.business_name,
            business_type=lead.business_type,
            years_in_business=lead.years_in_business,
            has_website=has_website,
            website_score=website_score,
            website_issues=website_issues,
            review_count=lead.review_count,
            price_level=lead.price_level,
            detected_cms=lead.detected_cms,
        )

        # Update lead with analysis
        lead.maturity_stage = report.maturity_stage
        lead.digital_readiness = report.digital_readiness
        lead.biggest_pain_point = report.biggest_pain_point
        lead.recommended_strategy = report.recommended_strategy
        lead.projected_roi_months = report.projected_roi_months
        lead.website_benefits = "\n".join(report.website_benefit_lines)

        # Get membership concept
        membership_concept = MembershipLibrary.get_concept(lead.business_type)
        membership_text = MembershipLibrary.format_for_pitch(lead.business_type) if membership_concept else ""
        lead.membership_idea = membership_text

        # Score the lead
        from src.business_intelligence import LeadScorer
        lead.lead_score = LeadScorer.score(
            years_in_business=lead.years_in_business,
            has_website=has_website,
            website_score=website_score,
            review_count=lead.review_count,
            rating=lead.rating,
        )

        db.commit()

        # Build rich context for AI pitch
        ctx = BusinessContext(
            name=lead.business_name,
            city=lead.city,
            business_type=lead.business_type,
            years_in_business=lead.years_in_business,
            has_website=has_website,
            website_score=website_score,
            website_issues=website_issues,
            linkedin_summary=web_data.get("summary") or "",
            offerings=web_data.get("offerings") or lead.menu_or_services or "",
            rating=lead.rating,
            review_count=lead.review_count,
            price_level=lead.price_level,
            maturity_stage=report.maturity_stage,
            biggest_pain_point=report.biggest_pain_point,
            membership_concept=membership_text,
            website_benefit_lines=report.website_benefit_lines,
        )

        # Generate pitch via AI Engine
        try:
            pitch_result = self.ai_engine.generate(db, ctx)
        except Exception as exc:
            logger.error("AI engine failed for %s: %s", lead.business_name, exc)
            pitch_result = self.ai_engine._template_fallback(ctx)

        return {
            "years_in_business": web_data.get("years"),
            "menu_or_services": web_data.get("offerings"),
            "pitch_text": pitch_result["pitch_text"],
            "context_summary": pitch_result.get("context_summary", f"{lead.business_type} pitch"),
            "membership_idea": pitch_result.get("membership_idea", ""),
            "website_benefits": pitch_result.get("website_benefits", ""),
            "maturity_stage": report.maturity_stage,
            "lead_score": lead.lead_score,
        }

    def _enrich_from_website(self, lead: Lead) -> dict[str, Any]:
        """Scrape the business's own website for description and services."""
        result: dict[str, Any] = {"summary": "", "offerings": "", "years": None}
        if not lead.website:
            return result

        try:
            url = lead.website if lead.website.startswith("http") else "https://" + lead.website
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Meta description
            meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
                "meta", attrs={"property": "og:description"}
            )
            if meta:
                result["summary"] = meta.get("content", "").strip()

            # Fallback to h1
            h1 = soup.find("h1")
            if h1 and not result["summary"]:
                result["summary"] = h1.get_text(strip=True)

            # Gather services from common sections
            for section in soup.find_all(["section", "div"]):
                cls = " ".join(section.get("class", [])).lower()
                if any(k in cls for k in ["service", "offer", "menu", "what we do", "treatment", "specialty"]):
                    texts = [
                        p.get_text(strip=True)
                        for p in section.find_all(["p", "li"])
                        if len(p.get_text(strip=True)) > 10
                    ]
                    if texts:
                        result["offerings"] = "\n".join(texts[:5])
                        break

            # Try to guess years in business from text
            year_match = re.search(r"\b(19\d{2}|20\d{2})\b", result["summary"] + " " + result["offerings"])
            if year_match:
                from datetime import datetime
                founded = int(year_match.group(1))
                result["years"] = datetime.now().year - founded

        except Exception as exc:
            logger.debug("Website enrichment failed for %s: %s", lead.business_name, exc)

        return result

    @staticmethod
    def _fallback_pitch(lead: Lead, website_audit: dict[str, Any] | None = None) -> str:
        """Generic fallback pitch when AI fails."""
        audit_frag = ""
        if website_audit:
            if website_audit.get("audit_failed"):
                audit_frag = (
                    f"Your current site seems hard to reach or outdated — I can build "
                    f"something reliable and modern for you."
                )
            elif website_audit.get("overall_score") in ("poor", "needs_work"):
                issues = website_audit.get("layout_issues", [])
                old_tech = website_audit.get("old_tech_detected", [])
                issue_list = ", ".join(issues + old_tech) if (issues or old_tech) else "several issues"
                audit_frag = (
                    f"I noticed your current site has {issue_list}. I can rebuild it "
                    f"into a fast, mobile-friendly site that drives more customers."
                )
        audit_block = f"{audit_frag}\n\n" if audit_frag else ""
        return (
            f"Hi {lead.business_name} team,\n\n"
            f"I came across your business in {lead.city} and noticed you could benefit "
            f"from a modern, mobile-friendly website that helps customers find you, "
            f"learn what you offer, and get in touch easily.\n\n"
            f"{audit_block}"
            f"I build fast, beautiful websites tailored for local businesses like yours. "
            f"Would you be open to a quick chat about how a new site could drive more "
            f"customers your way?\n\n"
            f"Best regards"
        )
