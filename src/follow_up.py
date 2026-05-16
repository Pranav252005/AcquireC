"""Follow-up sequence engine for automated lead nurturing.

Schedules and generates context-aware follow-up messages based on lead engagement.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.models import FollowUp, Lead, OutreachChannel, OutreachStatus

logger = logging.getLogger(__name__)

# Default sequence: day offsets and message types
DEFAULT_SEQUENCE: list[dict[str, Any]] = [
    {
        "day": 3,
        "channel": "whatsapp",
        "template": "follow_up_3day",
        "tone": "gentle",
    },
    {
        "day": 7,
        "channel": "email",
        "template": "value_first",
        "tone": "educational",
    },
    {
        "day": 14,
        "channel": "whatsapp",
        "template": "final_offer",
        "tone": "direct",
    },
    {
        "day": 30,
        "channel": "email",
        "template": "newsletter_optin",
        "tone": "long_term",
    },
]


class FollowUpEngine:
    """Generate and schedule follow-up sequences for leads."""

    def __init__(self, sequence: list[dict[str, Any]] | None = None) -> None:
        self.sequence = sequence or DEFAULT_SEQUENCE

    def schedule_for_lead(
        self,
        db: Session,
        lead: Lead,
        initial_pitch: str,
        context_summary: str,
    ) -> list[FollowUp]:
        """Create follow-up records for a lead after initial outreach."""
        now = datetime.now(timezone.utc)
        scheduled: list[FollowUp] = []

        for step in self.sequence:
            scheduled_at = now + timedelta(days=step["day"])
            message = self._generate_message(
                lead,
                step["template"],
                step["tone"],
                initial_pitch,
                context_summary,
            )
            fu = FollowUp(
                lead_id=lead.id,
                sequence_day=step["day"],
                channel=OutreachChannel(step["channel"]),
                message_text=message,
                scheduled_at=scheduled_at,
                status=OutreachStatus.PENDING,
            )
            db.add(fu)
            scheduled.append(fu)

        db.commit()
        logger.info("Scheduled %d follow-ups for lead %d", len(scheduled), lead.id)
        return scheduled

    def get_pending_follow_ups(self, db: Session, before: datetime | None = None) -> list[FollowUp]:
        """Get all follow-ups that are due to be sent."""
        if before is None:
            before = datetime.now(timezone.utc)
        return (
            db.query(FollowUp)
            .filter(FollowUp.status == OutreachStatus.PENDING)
            .filter(FollowUp.scheduled_at <= before)
            .order_by(FollowUp.scheduled_at)
            .all()
        )

    def cancel_sequence(self, db: Session, lead_id: int) -> int:
        """Cancel all pending follow-ups for a lead (e.g., if they replied)."""
        count = (
            db.query(FollowUp)
            .filter(FollowUp.lead_id == lead_id)
            .filter(FollowUp.status == OutreachStatus.PENDING)
            .update({"status": OutreachStatus.SENT})
        )
        db.commit()
        logger.info("Cancelled %d follow-ups for lead %d", count, lead_id)
        return count

    def _generate_message(
        self,
        lead: Lead,
        template: str,
        tone: str,
        initial_pitch: str,
        context_summary: str,
    ) -> str:
        """Generate a follow-up message based on template and tone."""
        name = lead.business_name
        concept = lead.membership_idea or "a loyalty program"

        if template == "follow_up_3day":
            return (
                f"Hi {name} team, just following up on my message about building you a modern website "
                f"with {concept}. Did it reach you? Happy to answer any questions."
            )

        if template == "value_first":
            return (
                f"Hi {name} team, I wanted to share something: last month, a {lead.business_type} in {lead.city} "
                f"similar to yours launched a website with online booking. Their walk-ins increased by 25% in 6 weeks. "
                f"I thought of you because {context_summary[:100]}. Worth a 10-min chat?"
            )

        if template == "final_offer":
            return (
                f"Hi {name} team, this is my last message — I don't want to clutter your inbox. "
                f"I genuinely believe a website with {concept} could change how {name} attracts customers. "
                f"If now isn't the right time, just reply 'later' and I'll check back in 3 months."
            )

        if template == "newsletter_optin":
            return (
                f"Hi {name} team, I'm putting together a monthly email with digital tips specifically for "
                f"{lead.business_type} owners in {lead.city}. No pitches, just practical advice. "
                f"Reply 'YES' if you'd like to receive it."
            )

        # Default gentle follow-up
        return (
            f"Hi {name} team, following up on my message about your website. "
            f"Would love to show you how {concept} could work for your business."
        )
