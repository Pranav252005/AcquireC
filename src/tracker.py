"""Tracker module for lead deduplication and outreach logging."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models import Lead, LeadNote, Outreach, OutreachChannel, OutreachStatus


def get_or_create_lead(
    db: Session,
    city: str,
    business_name: str,
    defaults: dict[str, Any] | None = None,
) -> Lead:
    """Get existing lead by city+name or create new one."""
    lead = db.query(Lead).filter_by(city=city, business_name=business_name).first()
    if lead:
        if defaults:
            for key, value in defaults.items():
                if value is not None and getattr(lead, key) in (None, ""):
                    setattr(lead, key, value)
            db.commit()
        return lead
    data = {
        "city": city,
        "business_name": business_name,
        "business_type": defaults.get("business_type", "unknown") if defaults else "unknown",
        "address": defaults.get("address", "") if defaults else "",
        "google_maps_url": defaults.get("google_maps_url", "") if defaults else "",
    }
    if defaults:
        for key in ("phone", "email", "website", "linkedin_url", "linkedin_summary",
                    "years_in_business", "menu_or_services"):
            if key in defaults:
                data[key] = defaults[key]
    lead = Lead(**data)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def is_already_contacted(db: Session, city: str, business_name: str) -> bool:
    """Return True if lead has at least one SENT outreach."""
    lead = db.query(Lead).filter_by(city=city, business_name=business_name).first()
    if not lead:
        return False
    return (
        db.query(Outreach)
        .filter(Outreach.lead_id == lead.id, Outreach.status == OutreachStatus.SENT)
        .first()
        is not None
    )


def has_any_outreach(db: Session, city: str, business_name: str) -> bool:
    """Return True if lead exists and has any outreach record."""
    lead = db.query(Lead).filter_by(city=city, business_name=business_name).first()
    if not lead:
        return False
    return db.query(Outreach).filter(Outreach.lead_id == lead.id).first() is not None


def log_outreach(
    db: Session,
    lead_id: int,
    channel: OutreachChannel,
    message_text: str,
    context_summary: str,
    status: OutreachStatus = OutreachStatus.PENDING,
    error_message: str | None = None,
) -> Outreach:
    """Create an outreach record."""
    outreach = Outreach(
        lead_id=lead_id,
        channel=channel,
        message_text=message_text,
        context_summary=context_summary,
        status=status,
        error_message=error_message,
        sent_at=datetime.now(timezone.utc) if status == OutreachStatus.SENT else None,
    )
    db.add(outreach)
    db.commit()
    db.refresh(outreach)
    return outreach


def get_city_summary(db: Session, city: str) -> dict[str, int]:
    """Return counts for a given city."""
    total = db.query(Lead).filter_by(city=city).count()
    contacted = (
        db.query(Outreach)
        .join(Lead)
        .filter(Lead.city == city, Outreach.status == OutreachStatus.SENT)
        .count()
    )
    pending = (
        db.query(Outreach)
        .join(Lead)
        .filter(Lead.city == city, Outreach.status == OutreachStatus.PENDING)
        .count()
    )
    failed = (
        db.query(Outreach)
        .join(Lead)
        .filter(Lead.city == city, Outreach.status == OutreachStatus.FAILED)
        .count()
    )
    responded = (
        db.query(Outreach)
        .join(Lead)
        .filter(Lead.city == city, Outreach.status == OutreachStatus.RESPONDED)
        .count()
    )
    return {
        "total": total,
        "contacted": contacted,
        "pending": pending,
        "failed": failed,
        "responded": responded,
    }


def get_all_cities(db: Session) -> list[dict[str, Any]]:
    """Return summary for every city that has leads."""
    rows = (
        db.query(Lead.city, func.count(Lead.id).label("total"))
        .group_by(Lead.city)
        .all()
    )
    result = []
    for row in rows:
        summary = get_city_summary(db, row.city)
        result.append({"city": row.city, **summary})
    return result


def get_lead_detail(db: Session, lead_id: int) -> Lead | None:
    """Return lead with outreaches loaded."""
    return db.query(Lead).filter_by(id=lead_id).first()


def add_lead_note(db: Session, lead_id: int, note_text: str) -> LeadNote:
    """Add a manual note to a lead."""
    note = LeadNote(lead_id=lead_id, note_text=note_text)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def update_lead_stage(db: Session, lead_id: int, stage: str) -> Lead | None:
    """Update the kanban stage of a lead."""
    lead = db.query(Lead).filter_by(id=lead_id).first()
    if lead:
        lead.kanban_stage = stage
        db.commit()
    return lead


def update_lead_score(db: Session, lead_id: int, score: int) -> Lead | None:
    """Update the lead score."""
    lead = db.query(Lead).filter_by(id=lead_id).first()
    if lead:
        lead.lead_score = max(0, min(100, score))
        db.commit()
    return lead


def get_hot_leads(db: Session, min_score: int = 70, limit: int = 50) -> list[Lead]:
    """Return high-scoring leads that need attention."""
    return (
        db.query(Lead)
        .filter(Lead.lead_score >= min_score)
        .order_by(Lead.lead_score.desc())
        .limit(limit)
        .all()
    )


def get_leads_by_stage(db: Session, stage: str, city: str | None = None) -> list[Lead]:
    """Return leads in a specific kanban stage."""
    query = db.query(Lead).filter(Lead.kanban_stage == stage)
    if city:
        query = query.filter(Lead.city.ilike(f"%{city}%"))
    return query.order_by(Lead.updated_at.desc()).all()


def update_lead_reply_intent(db: Session, lead_id: int, intent: str) -> Lead | None:
    """Update lead status to RESPONDED and set reply intent metadata."""
    lead = db.query(Lead).filter_by(id=lead_id).first()
    if lead:
        lead.kanban_stage = "replied"
        db.commit()
    return lead


def get_outreach_stats(db: Session) -> dict[str, int]:
    """Return outreach counts by status using SQL GROUP BY."""
    rows = db.query(Outreach.status, func.count(Outreach.id)).group_by(Outreach.status).all()
    stats = {"contacted": 0, "failed": 0, "responded": 0, "pending": 0}
    for status, count in rows:
        if status == OutreachStatus.SENT:
            stats["contacted"] = count
        elif status == OutreachStatus.FAILED:
            stats["failed"] = count
        elif status == OutreachStatus.RESPONDED:
            stats["responded"] = count
        elif status == OutreachStatus.PENDING:
            stats["pending"] = count
    return stats
