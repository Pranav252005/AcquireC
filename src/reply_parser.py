"""Reply intent classification for incoming lead responses.

Uses keyword-based classification (v1) with optional LLM fallback (v2).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from src.models import Lead, ReplyIntent

logger = logging.getLogger(__name__)


@dataclass
class ParsedReply:
    """Result of parsing a lead reply."""

    intent: ReplyIntent
    confidence: float
    extracted_info: dict[str, Any]
    suggested_action: str


class ReplyParser:
    """Classify incoming replies from leads into actionable intents."""

    # Keyword patterns for intent detection
    PATTERNS: dict[ReplyIntent, list[str]] = {
        ReplyIntent.INTERESTED: [
            r"\btell me more\b",
            r"\bsounds good\b",
            r"\binterested\b",
            r"\bintere\w*\b",
            r"\bwould like to\b",
            r"\bkeen\b",
            r"\blove to\b",
            r"\bopen to\b",
            r"\bup for\b",
            r"\blet.s (talk|chat|discuss)\b",
            r"\bcall me\b",
            r"\bsend me\b",
            r"\bshow me\b",
            r"\bok\b",
            r"\byes\b",
            r"\bsure\b",
            r"\bgo ahead\b",
            r"\bproceed\b",
        ],
        ReplyIntent.PRICE_INQUIRY: [
            r"\bhow much\b",
            r"\bprice\b",
            r"\bcost\b",
            r"\bpricing\b",
            r"\bquote\b",
            r"\bestimate\b",
            r"\bbudget\b",
            r"\bwhat.s the (rate|charge|fee)\b",
            r"\baffordable\b",
            r"\bexpensive\b",
            r"\bcheaper\b",
        ],
        ReplyIntent.NOT_NOW: [
            r"\bnot now\b",
            r"\blater\b",
            r"\bmaybe later\b",
            r"\btoo busy\b",
            r"\bbusy\b",
            r"\bnext (month|week|year)\b",
            r"\bnot the right time\b",
            r"\bnot interested right now\b",
            r"\bcontact me later\b",
            r"\bfollow up\b",
        ],
        ReplyIntent.NOT_INTERESTED: [
            r"\bnot interested\b",
            r"\bno thanks\b",
            r"\bunsubscribe\b",
            r"\bstop\b",
            r"\bdon.t (contact|message|call)\b",
            r"\bremove\b",
            r"\bspam\b",
            r"\bnever\b",
            r"\bnot required\b",
            r"\balready have\b",
            r"\bdon.t need\b",
        ],
        ReplyIntent.BOOKED: [
            r"\b(call|meet) (me )?on\b",
            r"\b(call|meet) (me )?at\b",
            r"\bavailable on\b",
            r"\bfree on\b",
            r"\bschedule\b",
            r"\bbook\b",
            r"\bappointment\b",
            r"\btomorrow\b",
            r"\bmonday\b",
            r"\btuesday\b",
            r"\bwednesday\b",
            r"\bthursday\b",
            r"\bfriday\b",
            r"\bsaturday\b",
            r"\bsunday\b",
            r"\b\d{1,2}(:\d{2})?\s*(am|pm)\b",
            r"\b\d{1,2}\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b",
        ],
    }

    @classmethod
    def parse(cls, reply_text: str, lead: Lead | None = None) -> ParsedReply:
        """Classify reply text into intent with confidence score."""
        text_lower = reply_text.lower().strip()

        # Empty or very short
        if len(text_lower) < 3:
            return ParsedReply(
                intent=ReplyIntent.UNKNOWN,
                confidence=0.0,
                extracted_info={},
                suggested_action="Ignore or request clarification",
            )

        scores: dict[ReplyIntent, int] = {}
        for intent, patterns in cls.PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    score += 1
            scores[intent] = score

        # Determine winner — NOT_INTERESTED and NOT_NOW take precedence over INTERESTED
        priority_order = [ReplyIntent.NOT_INTERESTED, ReplyIntent.NOT_NOW, ReplyIntent.BOOKED, ReplyIntent.PRICE_INQUIRY, ReplyIntent.INTERESTED]
        best_intent = ReplyIntent.UNKNOWN
        best_score = 0
        if scores:
            best_intent = max(scores, key=lambda k: scores[k])
            best_score = scores[best_intent]
            # Apply priority: if a high-priority intent has any match, prefer it
            for intent in priority_order:
                if scores.get(intent, 0) > 0 and scores.get(intent, 0) >= best_score - 1:
                    best_intent = intent
                    best_score = scores[intent]
                    break

        total_hits = sum(scores.values())
        confidence = best_score / max(total_hits, 1)

        # Extract info
        extracted: dict[str, Any] = {}
        phone_match = re.search(r"[\+]?[\d\s\-\(\)]{7,20}", reply_text)
        if phone_match:
            extracted["phone"] = phone_match.group(0)
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}", reply_text)
        if email_match:
            extracted["email"] = email_match.group(0)

        # Suggested actions
        actions = {
            ReplyIntent.INTERESTED: "Send pricing guide + calendar link. Mark as HOT lead.",
            ReplyIntent.PRICE_INQUIRY: "Auto-reply with pricing PDF. Alert user immediately.",
            ReplyIntent.NOT_NOW: "Reschedule follow-up for 30 days. Tag as 'nurture'.",
            ReplyIntent.NOT_INTERESTED: "Unsubscribe and mark as LOST. No more outreach.",
            ReplyIntent.BOOKED: "Mark as MEETING BOOKED. Alert user with details.",
            ReplyIntent.UNKNOWN: "Flag for manual review.",
        }

        # Override confidence thresholds
        if best_score == 0:
            best_intent = ReplyIntent.UNKNOWN
            confidence = 0.0
        elif best_intent == ReplyIntent.NOT_INTERESTED and best_score >= 1:
            confidence = min(1.0, confidence + 0.3)  # Strong negative signal

        logger.info(
            "Parsed reply for lead %s: intent=%s confidence=%.2f",
            lead.business_name if lead else "unknown",
            best_intent.value,
            confidence,
        )

        return ParsedReply(
            intent=best_intent,
            confidence=confidence,
            extracted_info=extracted,
            suggested_action=actions.get(best_intent, "Review manually"),
        )

    @classmethod
    def auto_reply(cls, parsed: ParsedReply, lead: Lead) -> str | None:
        """Generate an auto-reply for certain intents."""
        if parsed.intent == ReplyIntent.PRICE_INQUIRY:
            return (
                f"Thanks for your interest, {lead.business_name} team! "
                f"I've attached a simple pricing guide. Most {lead.business_type} businesses in {lead.city} "
                f"start with a package between ₹15,000-₹35,000 depending on features. "
                f"Happy to discuss what's right for you — just reply with a time that works."
            )

        if parsed.intent == ReplyIntent.INTERESTED:
            return (
                f"Great to hear from you, {lead.business_name} team! "
                f"I'd love to show you exactly how this would look for your business. "
                f"Do you have 15 minutes this week? I'm free Tuesday-Thursday afternoons."
            )

        return None
