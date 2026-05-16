"""Daily reporting module for organized lead data and pipeline summaries.

Creates a folder structure like:
    reports/
        2026-05-16/
            summary.json          — overall stats for the day
            leads.csv             — all leads discovered today
            by-city/
                Mumbai.csv
                Delhi.csv
            by-category/
                cafe.csv
                salon.csv
            by-contact/
                with_both.csv     — has email + phone
                email_only.csv
                phone_only.csv
                no_contact.csv
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from src.models import Lead, OutreachStatus
from src.tracker import get_city_summary

logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports")


@dataclass
class DailySummary:
    """Summary of a day's pipeline run."""

    date: str
    total_discovered: int
    total_processed: int
    total_sent: int
    total_failed: int
    total_skipped: int
    cities: list[str]
    categories: list[str]
    leads_with_both_contacts: int
    leads_with_email_only: int
    leads_with_phone_only: int
    leads_with_no_contact: int
    by_city: dict[str, dict[str, Any]]
    by_category: dict[str, dict[str, Any]]


def _today_dir() -> Path:
    """Return today's report directory, creating it if needed."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = REPORTS_DIR / today
    path.mkdir(parents=True, exist_ok=True)
    (path / "by-city").mkdir(exist_ok=True)
    (path / "by-category").mkdir(exist_ok=True)
    (path / "by-contact").mkdir(exist_ok=True)
    return path


def _lead_to_row(lead: Lead) -> dict[str, Any]:
    """Convert a Lead to a flat dict for CSV export."""
    latest_status = "none"
    if lead.outreaches:
        for o in reversed(lead.outreaches):
            if o.status != OutreachStatus.PENDING:
                latest_status = o.status.value
                break
    return {
        "id": lead.id,
        "business_name": lead.business_name,
        "city": lead.city,
        "business_type": lead.business_type,
        "address": lead.address,
        "phone": lead.phone or "",
        "email": lead.email or "",
        "website": lead.website or "",
        "google_maps_url": lead.google_maps_url,
        "rating": lead.rating or "",
        "review_count": lead.review_count or "",
        "price_level": lead.price_level or "",
        "years_in_business": lead.years_in_business or "",
        "maturity_stage": lead.maturity_stage or "",
        "lead_score": lead.lead_score or "",
        "kanban_stage": lead.kanban_stage or "cold",
        "membership_idea": (lead.membership_idea or "")[:200],
        "latest_status": latest_status,
        "created_at": lead.created_at.isoformat() if lead.created_at else "",
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write rows to a CSV file."""
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_daily_report(
    db: Session,
    discovered_leads: list[dict[str, Any]],
    processed_leads: list[Lead],
    sent: int,
    failed: int,
    skipped: int,
    cities: list[str],
    categories: list[str],
) -> Path:
    """Generate and save a complete daily report package.

    Returns the path to today's report directory.
    """
    base = _today_dir()
    timestamp = datetime.now(timezone.utc).strftime("%H-%M-%S")

    # Categorize processed leads by contact availability
    both, email_only, phone_only, no_contact = [], [], [], []
    for lead in processed_leads:
        has_email = bool(lead.email)
        has_phone = bool(lead.phone)
        if has_email and has_phone:
            both.append(lead)
        elif has_email:
            email_only.append(lead)
        elif has_phone:
            phone_only.append(lead)
        else:
            no_contact.append(lead)

    # Write contact-segregated CSVs
    _write_csv(base / "by-contact" / "with_both.csv", [_lead_to_row(l) for l in both])
    _write_csv(base / "by-contact" / "email_only.csv", [_lead_to_row(l) for l in email_only])
    _write_csv(base / "by-contact" / "phone_only.csv", [_lead_to_row(l) for l in phone_only])
    _write_csv(base / "by-contact" / "no_contact.csv", [_lead_to_row(l) for l in no_contact])

    # Write city CSVs
    for city in cities:
        city_leads = [l for l in processed_leads if l.city.lower() == city.lower()]
        _write_csv(base / "by-city" / f"{city}.csv", [_lead_to_row(l) for l in city_leads])

    # Write category CSVs
    for category in categories:
        cat_leads = [l for l in processed_leads if l.business_type.lower() == category.lower()]
        _write_csv(base / "by-category" / f"{category}.csv", [_lead_to_row(l) for l in cat_leads])

    # Write all processed leads
    _write_csv(base / "leads.csv", [_lead_to_row(l) for l in processed_leads])

    # Build by-city stats
    by_city_stats: dict[str, dict[str, Any]] = {}
    for city in cities:
        summary = get_city_summary(db, city)
        by_city_stats[city] = {
            "total_leads": summary["total"],
            "contacted": summary["contacted"],
            "responded": summary["responded"],
            "failed": summary["failed"],
        }

    # Build by-category stats
    by_category_stats: dict[str, dict[str, Any]] = {}
    for category in categories:
        cat_leads = [l for l in processed_leads if l.business_type.lower() == category.lower()]
        by_category_stats[category] = {
            "discovered": len([d for d in discovered_leads if d.get("business_type", "").lower() == category.lower()]),
            "processed": len(cat_leads),
            "with_both_contacts": len([l for l in cat_leads if l.email and l.phone]),
            "with_email_only": len([l for l in cat_leads if l.email and not l.phone]),
            "with_phone_only": len([l for l in cat_leads if l.phone and not l.email]),
            "with_no_contact": len([l for l in cat_leads if not l.email and not l.phone]),
        }

    summary = DailySummary(
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        total_discovered=len(discovered_leads),
        total_processed=len(processed_leads),
        total_sent=sent,
        total_failed=failed,
        total_skipped=skipped,
        cities=cities,
        categories=categories,
        leads_with_both_contacts=len(both),
        leads_with_email_only=len(email_only),
        leads_with_phone_only=len(phone_only),
        leads_with_no_contact=len(no_contact),
        by_city=by_city_stats,
        by_category=by_category_stats,
    )

    summary_path = base / f"summary_{timestamp}.json"
    summary_path.write_text(json.dumps(asdict(summary), indent=2, default=str), encoding="utf-8")

    # Also write a human-readable summary text file
    text_path = base / f"summary_{timestamp}.txt"
    lines = [
        f"DAILY REPORT — {summary.date}",
        "=" * 50,
        f"Cities searched      : {', '.join(cities)}",
        f"Categories searched  : {', '.join(categories)}",
        f"Total discovered     : {summary.total_discovered}",
        f"Total processed      : {summary.total_processed}",
        f"Messages sent        : {summary.total_sent}",
        f"Messages failed      : {summary.total_failed}",
        f"Skipped              : {summary.total_skipped}",
        "",
        "CONTACT BREAKDOWN",
        "-" * 30,
        f"Both email + phone   : {summary.leads_with_both_contacts}",
        f"Email only           : {summary.leads_with_email_only}",
        f"Phone only           : {summary.leads_with_phone_only}",
        f"No contact           : {summary.leads_with_no_contact}",
        "",
        "BY CATEGORY",
        "-" * 30,
    ]
    for cat, stats in by_category_stats.items():
        lines.append(
            f"{cat:15s} | Discovered: {stats['discovered']:3d} | Processed: {stats['processed']:3d} | "
            f"Both: {stats['with_both_contacts']:3d} | Email: {stats['with_email_only']:3d} | "
            f"Phone: {stats['with_phone_only']:3d} | None: {stats['with_no_contact']:3d}"
        )
    lines.append("")
    lines.append("FILES GENERATED")
    lines.append("-" * 30)
    lines.append(f"All leads        : {base / 'leads.csv'}")
    lines.append(f"With both        : {base / 'by-contact' / 'with_both.csv'}")
    lines.append(f"Email only       : {base / 'by-contact' / 'email_only.csv'}")
    lines.append(f"Phone only       : {base / 'by-contact' / 'phone_only.csv'}")
    lines.append(f"No contact       : {base / 'by-contact' / 'no_contact.csv'}")
    lines.append(f"JSON summary     : {summary_path}")

    text_path.write_text("\n".join(lines), encoding="utf-8")

    logger.info("Daily report saved to %s", base)
    return base


def list_report_dates() -> list[str]:
    """Return all available report dates (folder names)."""
    if not REPORTS_DIR.exists():
        return []
    return sorted([d.name for d in REPORTS_DIR.iterdir() if d.is_dir()], reverse=True)


def get_report_for_date(date_str: str) -> Path | None:
    """Return the report directory for a specific date."""
    path = REPORTS_DIR / date_str
    if path.exists():
        return path
    return None
