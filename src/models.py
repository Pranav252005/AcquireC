"""SQLAlchemy models for lead tracking."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base declarative class."""


class OutreachChannel(str, enum.Enum):
    """Communication channel."""

    EMAIL = "email"
    WHATSAPP = "whatsapp"


class OutreachStatus(str, enum.Enum):
    """Status of an outreach attempt."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RESPONDED = "responded"
    CANCELLED = "cancelled"


class ReplyIntent(str, enum.Enum):
    """Classified intent of a lead reply."""

    INTERESTED = "interested"
    PRICE_INQUIRY = "price_inquiry"
    NOT_NOW = "not_now"
    NOT_INTERESTED = "not_interested"
    BOOKED = "booked"
    SPAM = "spam"
    UNKNOWN = "unknown"


class Lead(Base):
    """A discovered local business."""

    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("city", "business_name", name="uq_lead_city_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    business_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    business_type: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")
    address: Mapped[str] = mapped_column(Text, nullable=False, default="")
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    google_maps_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linkedin_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    years_in_business: Mapped[int | None] = mapped_column(Integer, nullable=True)
    menu_or_services: Mapped[str | None] = mapped_column(Text, nullable=True)
    website_audit: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # New enrichment fields
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_level: Mapped[str | None] = mapped_column(String(10), nullable=True)  # $ to $$$$
    photo_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detected_cms: Mapped[str | None] = mapped_column(String(50), nullable=True)  # wordpress, wix, etc.
    maturity_stage: Mapped[str | None] = mapped_column(String(20), nullable=True)  # startup, growth, established, legacy
    digital_readiness: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-10
    lead_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-100
    kanban_stage: Mapped[str | None] = mapped_column(String(20), nullable=True, default="cold")  # cold, pitched, replied, meeting, closed, lost

    # AI-generated strategy fields
    membership_idea: Mapped[str | None] = mapped_column(Text, nullable=True)
    website_benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    biggest_pain_point: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_strategy: Mapped[str | None] = mapped_column(Text, nullable=True)
    projected_roi_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )

    outreaches: Mapped[list["Outreach"]] = relationship(
        "Outreach", back_populates="lead", cascade="all, delete-orphan", lazy="selectin"
    )
    follow_ups: Mapped[list["FollowUp"]] = relationship(
        "FollowUp", back_populates="lead", cascade="all, delete-orphan", lazy="selectin"
    )
    notes: Mapped[list["LeadNote"]] = relationship(
        "LeadNote", back_populates="lead", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, name={self.business_name}, city={self.city})>"


class Outreach(Base):
    """An outreach attempt to a lead."""

    __tablename__ = "outreaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[OutreachChannel] = mapped_column(
        Enum(OutreachChannel), nullable=False
    )
    message_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    context_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[OutreachStatus] = mapped_column(
        Enum(OutreachStatus), nullable=False, default=OutreachStatus.PENDING
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, nullable=False
    )

    lead: Mapped["Lead"] = relationship("Lead", back_populates="outreaches")

    def __repr__(self) -> str:
        return (
            f"<Outreach(id={self.id}, lead_id={self.lead_id}, "
            f"channel={self.channel.value}, status={self.status.value})>"
        )


class PitchCache(Base):
    """Cache for successful AI-generated pitches to reduce API calls."""

    __tablename__ = "pitch_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    context_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    business_type: Mapped[str] = mapped_column(String(100), nullable=False)
    maturity_stage: Mapped[str] = mapped_column(String(20), nullable=False)
    website_score: Mapped[str] = mapped_column(String(20), nullable=False)
    pitch_text: Mapped[str] = mapped_column(Text, nullable=False)
    membership_idea: Mapped[str] = mapped_column(Text, nullable=False)
    website_benefits: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(String(50), nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<PitchCache(id={self.id}, type={self.business_type}, stage={self.maturity_stage})>"


class FollowUp(Base):
    """Scheduled follow-up for a lead."""

    __tablename__ = "follow_ups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence_day: Mapped[int] = mapped_column(Integer, nullable=False)  # 0, 3, 7, 14, 30
    channel: Mapped[OutreachChannel] = mapped_column(Enum(OutreachChannel), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[OutreachStatus] = mapped_column(
        Enum(OutreachStatus), nullable=False, default=OutreachStatus.PENDING
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)

    lead: Mapped["Lead"] = relationship("Lead", back_populates="follow_ups")

    def __repr__(self) -> str:
        return f"<FollowUp(id={self.id}, lead_id={self.lead_id}, day={self.sequence_day})>"


class DiscoveryAlert(Base):
    """Alerts shown in the dashboard when a city+category is exhausted."""

    __tablename__ = "discovery_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    alert_type: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")
    dismissed: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<DiscoveryAlert(city={self.city}, category={self.category}, type={self.alert_type})>"


class LeadNote(Base):
    """Manual notes added to a lead."""

    __tablename__ = "lead_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)

    lead: Mapped["Lead"] = relationship("Lead", back_populates="notes")

    def __repr__(self) -> str:
        return f"<LeadNote(id={self.id}, lead_id={self.lead_id})>"
