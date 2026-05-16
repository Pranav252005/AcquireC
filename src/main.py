"""CLI entry point for the client acquisition system."""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from sqlalchemy.orm import Session

from src.config import get_settings
from src.dashboard import run_dashboard as start_dashboard
from src.database import get_sessionmaker, init_db
from src.discovery import DiscoveryError, GoogleMapsScraper
from src.follow_up import FollowUpEngine
from src.messenger import EmailSender, WhatsAppError, WhatsAppSender
from src.models import Lead, OutreachChannel, OutreachStatus
from src.reports import list_report_dates, save_daily_report
from src.researcher import LinkedInResearcher
from src.website_auditor import WebsiteAuditor
from src.summarizer import Summarizer
from src.tracker import (
    get_all_cities,
    get_city_summary,
    get_hot_leads,
    get_leads_by_stage,
    get_or_create_lead,
    is_already_contacted,
    log_outreach,
    update_lead_stage,
)

console = Console()
logger = logging.getLogger(__name__)


def get_db() -> Session:
    """Return a new DB session."""
    engine = init_db()
    SessionLocal = get_sessionmaker(engine)
    return SessionLocal()


def _whatsapp_draft_path(city: str) -> Path:
    """Return a single file path for WhatsApp drafts for this run."""
    settings = get_settings()
    drafts_dir = settings.whatsapp_drafts_path
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{city.replace(' ', '_')}_{timestamp}.txt"
    return drafts_dir / filename


def _append_whatsapp_draft(draft_path: Path, lead: Lead, pitch: str) -> None:
    """Append a lead's WhatsApp draft to the given file."""
    block = (
        f"========================================\n"
        f"Business : {lead.business_name}\n"
        f"Phone    : {lead.phone}\n"
        f"Email    : {lead.email}\n"
        f"City     : {lead.city}\n"
        f"Type     : {lead.business_type}\n"
        f"Score    : {lead.lead_score or 'N/A'}\n"
        f"Stage    : {lead.maturity_stage or 'N/A'}\n"
        f"----------------------------------------\n"
        f"{pitch}\n"
        f"========================================\n\n"
    )
    with draft_path.open("a", encoding="utf-8") as f:
        f.write(block)


def _extract_email_from_website(website: str) -> str | None:
    """Try to find a contact email by checking common pages."""
    # This is a placeholder for email extraction heuristic.
    # In production, you could scrape /contact, /about pages for mailto: links.
    return None


def run_pipeline(
    city: str,
    category: str,
    max_leads: int,
    skip_contacted: bool = True,
    channels: list[str] | None = None,
    auto_send: bool = False,
    enable_follow_up: bool = True,
    require_both_contacts: bool = False,
) -> dict[str, Any]:
    """Run the full discovery → research → outreach pipeline for one city+category."""
    if channels is None:
        channels = ["email"]

    db = get_db()
    stats = get_city_summary(db, city)
    console.print(
        Panel.fit(
            f"[bold]{city}[/bold] — {category} — Already contacted [green]{stats['contacted']}[/green] / "
            f"[red]{stats['failed']}[/red] failed out of [blue]{stats['total']}[/blue] total leads"
        )
    )

    if stats["total"] > 0 and skip_contacted:
        console.print("[dim]Skipping already-contacted businesses.[/dim]")

    # WhatsApp auth upfront if needed
    wa_sender = None
    if "whatsapp" in channels:
        console.print("\n[yellow]Opening WhatsApp Web for authentication...[/yellow]")
        wa_sender = WhatsAppSender()
        if not wa_sender.ensure_auth():
            console.print("[red]WhatsApp authentication failed. Messages will be skipped.[/red]")
            channels = [c for c in channels if c != "whatsapp"]
            wa_sender.close()
            wa_sender = None
        else:
            console.print("[green]WhatsApp Web authenticated.[/green]\n")

    # Discovery
    console.print(f"[bold blue]Step 1: Discovering {category} businesses in {city} on Google Maps...[/bold blue]")
    scraper = GoogleMapsScraper(headless=True)
    try:
        raw_leads = scraper.discover(city, category, max_leads=max_leads * 3)
    except DiscoveryError as exc:
        console.print(f"[red]Discovery failed: {exc}[/red]")
        db.close()
        return {"error": str(exc), "city": city, "category": category}

    # Website audit filter: skip businesses with modern websites
    auditor = WebsiteAuditor(headless=True)
    website_skipped = 0
    audited_leads = []
    for data in raw_leads:
        website = data.get("website")
        if website:
            audit = auditor.audit(website)
            data["website_audit"] = audit
            data["detected_cms"] = audit.get("detected_cms")
            # Try to extract email from website if missing
            if not data.get("email"):
                extracted = _extract_email_from_website(website)
                if extracted:
                    data["email"] = extracted
            if audit.get("overall_score") == "good" and not audit.get("audit_failed"):
                console.print(f"[dim]{data['business_name']}: Website looks modern, skipping.[/dim]")
                website_skipped += 1
                continue
        audited_leads.append(data)

    # Dedup filter
    leads_to_process = []
    skipped = 0
    for data in audited_leads:
        if is_already_contacted(db, city, data["business_name"]):
            skipped += 1
            continue
        leads_to_process.append(data)
        if len(leads_to_process) >= max_leads:
            break

    console.print(
        f"[green]Found {len(raw_leads)} results, "
        f"{len(leads_to_process)} new to process, "
        f"{skipped} already contacted, "
        f"{website_skipped} skipped (good website).[/green]\n"
    )

    if not leads_to_process:
        console.print("[yellow]No new leads to process.[/yellow]")
        db.close()
        return {"found": 0, "sent": 0, "failed": 0, "skipped": skipped, "city": city, "category": category, "leads": []}

    # Research + Outreach
    researcher = LinkedInResearcher(headless=True)
    email_sender = EmailSender() if "email" in channels else None
    follow_up_engine = FollowUpEngine() if enable_follow_up else None

    sent_count = 0
    failed_count = 0
    skip_count = 0
    draft_path = _whatsapp_draft_path(city) if "whatsapp" not in channels else None
    processed_db_leads: list[Lead] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for idx, data in enumerate(leads_to_process, 1):
            task = progress.add_task(f"[{idx}/{len(leads_to_process)}] {data['business_name']} ...", total=None)

            # Get or create lead
            lead = get_or_create_lead(db, city, data["business_name"], defaults=data)
            processed_db_leads.append(lead)

            # Persist new enrichment fields
            for key in ("rating", "review_count", "price_level", "detected_cms"):
                if key in data and data[key] is not None:
                    setattr(lead, key, data[key])

            # Persist website audit if present
            audit = data.get("website_audit")
            if audit:
                lead.website_audit = audit
                lead.detected_cms = audit.get("detected_cms")
                db.commit()

            # Contact info check
            has_email = bool(lead.email)
            has_phone = bool(lead.phone)

            # If require_both_contacts is set, skip unless both are present
            if require_both_contacts and not (has_email and has_phone):
                progress.update(task, description=f"[yellow]{data['business_name']} — missing contact, skipped[/yellow]")
                skip_count += 1
                continue

            # Skip if no contact info at all and we need to message
            if not has_email and not has_phone:
                progress.update(task, description=f"[yellow]{data['business_name']} — no contact info, skipped[/yellow]")
                skip_count += 1
                continue

            # Research
            progress.update(task, description=f"Researching {data['business_name']} ...")
            try:
                enriched = researcher.research(db, lead, website_audit=audit)
                for key in ("linkedin_url", "linkedin_summary", "years_in_business", "menu_or_services",
                            "membership_idea", "website_benefits", "maturity_stage", "lead_score"):
                    if enriched.get(key) is not None:
                        setattr(lead, key, enriched[key])
                db.commit()
            except Exception as exc:
                console.print(f"[dim]Research error for {data['business_name']}: {exc}[/dim]")
                enriched = {
                    "pitch_text": researcher._fallback_pitch(lead, website_audit=audit),
                    "context_summary": f"Generic pitch for {lead.business_type}",
                    "membership_idea": "",
                    "website_benefits": "",
                }

            pitch = enriched.get("pitch_text", researcher._fallback_pitch(lead, website_audit=audit))
            context = enriched.get("context_summary", f"{lead.business_type} pitch")
            membership = enriched.get("membership_idea", "")

            # Update kanban stage
            update_lead_stage(db, lead.id, "pitched")

            # Show pitch and ask (or auto-send)
            progress.stop()
            console.print(f"\n[bold]{lead.business_name}[/bold] — {lead.city}")
            console.print(f"[dim]Type: {lead.business_type} | Stage: {lead.maturity_stage or 'N/A'} | Score: {lead.lead_score or 'N/A'}[/dim]")
            console.print(f"[dim]Phone: {lead.phone or 'N/A'} | Email: {lead.email or 'N/A'}[/dim]")
            console.print(Panel(pitch[:500] + ("..." if len(pitch) > 500 else ""), title="Generated Pitch", border_style="blue"))
            if membership:
                console.print(Panel(membership[:300] + ("..." if len(membership) > 300 else ""), title="Membership Concept", border_style="green"))

            if auto_send:
                action = "y"
                console.print("[dim]Auto-send enabled.[/dim]")
            else:
                action = Prompt.ask(
                    "Send?",
                    choices=["y", "n", "e", "s"],
                    default="y",
                    show_choices=True,
                )
            if action == "s":
                skip_count += 1
                progress.start()
                continue
            if action == "n":
                progress.start()
                continue
            if action == "e":
                pitch = Prompt.ask("Edit pitch", default=pitch)

            # Save WhatsApp draft if channel is skipped but phone exists
            if draft_path and lead.phone:
                _append_whatsapp_draft(draft_path, lead, pitch)
                console.print(f"[cyan]  → WhatsApp draft saved for {lead.business_name}[/cyan]")

            # Send
            channels_to_try = []
            if "email" in channels and has_email:
                channels_to_try.append("email")
            if "whatsapp" in channels and has_phone:
                channels_to_try.append("whatsapp")

            for ch in channels_to_try:
                try:
                    if ch == "email" and email_sender:
                        subject = f"A quick idea for {lead.business_name}'s next {lead.years_in_business or 'few'} years"
                        email_sender.send(lead.email, subject, pitch)
                        log_outreach(
                            db, lead.id, OutreachChannel.EMAIL, pitch, context, status=OutreachStatus.SENT
                        )
                        console.print(f"[green]  ✓ Email sent to {lead.email}[/green]")
                        sent_count += 1
                    elif ch == "whatsapp" and wa_sender:
                        wa_sender.send(lead.phone, pitch)
                        log_outreach(
                            db, lead.id, OutreachChannel.WHATSAPP, pitch, context, status=OutreachStatus.SENT
                        )
                        console.print(f"[green]  ✓ WhatsApp sent to {lead.phone}[/green]")
                        sent_count += 1
                except Exception as exc:
                    log_outreach(
                        db, lead.id,
                        OutreachChannel.EMAIL if ch == "email" else OutreachChannel.WHATSAPP,
                        pitch, context, status=OutreachStatus.FAILED, error_message=str(exc)[:500]
                    )
                    console.print(f"[red]  ✗ {ch.capitalize()} failed: {exc}[/red]")
                    failed_count += 1

            # Schedule follow-ups if outreach was sent
            if enable_follow_up and follow_up_engine and sent_count > 0:
                try:
                    follow_up_engine.schedule_for_lead(db, lead, pitch, context)
                except Exception as exc:
                    console.print(f"[dim]Follow-up scheduling failed: {exc}[/dim]")

            progress.start()

    if wa_sender:
        wa_sender.close()

    db.close()
    summary = f"[bold]Done:[/bold] {sent_count} sent, {failed_count} failed, {skip_count} skipped, {skipped} already contacted."
    if draft_path:
        summary += f"\n[cyan]Drafts saved to {draft_path}[/cyan]"
    console.print(f"\n{summary}")
    result = {
        "found": len(leads_to_process),
        "sent": sent_count,
        "failed": failed_count,
        "skipped": skipped + skip_count,
        "city": city,
        "category": category,
        "leads": processed_db_leads,
    }
    if draft_path:
        result["draft_path"] = str(draft_path)
    return result


def run_multi_pipeline(
    cities: list[str],
    categories: list[str],
    max_leads_per_combo: int,
    skip_contacted: bool = True,
    channels: list[str] | None = None,
    auto_send: bool = False,
    enable_follow_up: bool = True,
    require_both_contacts: bool = False,
) -> dict[str, Any]:
    """Run pipeline across multiple cities and categories."""
    all_discovered: list[dict[str, Any]] = []
    all_processed: list[Lead] = []
    total_sent = 0
    total_failed = 0
    total_skipped = 0

    total_combos = len(cities) * len(categories)
    combo_idx = 0

    for city in cities:
        for category in categories:
            combo_idx += 1
            console.print(Panel.fit(f"[bold cyan]Combo {combo_idx}/{total_combos}: {category} in {city}[/bold cyan]"))
            result = run_pipeline(
                city=city,
                category=category,
                max_leads=max_leads_per_combo,
                skip_contacted=skip_contacted,
                channels=channels,
                auto_send=auto_send,
                enable_follow_up=enable_follow_up,
                require_both_contacts=require_both_contacts,
            )
            if "error" not in result:
                all_discovered.extend([{"city": city, "category": category, **(l if isinstance(l, dict) else {"business_name": l.business_name})} for l in result.get("leads", [])])
                all_processed.extend(result.get("leads", []))
                total_sent += result.get("sent", 0)
                total_failed += result.get("failed", 0)
                total_skipped += result.get("skipped", 0)
            # Small delay between combos to avoid rate limits
            time.sleep(2)

    # Save daily report
    db = get_db()
    report_dir = save_daily_report(
        db=db,
        discovered_leads=all_discovered,
        processed_leads=all_processed,
        sent=total_sent,
        failed=total_failed,
        skipped=total_skipped,
        cities=cities,
        categories=categories,
    )
    db.close()

    console.print(f"\n[bold green]All combos complete![/bold green]")
    console.print(f"[green]Total sent: {total_sent}, failed: {total_failed}, skipped: {total_skipped}[/green]")
    console.print(f"[cyan]Daily report saved to: {report_dir}[/cyan]")

    return {
        "total_sent": total_sent,
        "total_failed": total_failed,
        "total_skipped": total_skipped,
        "report_dir": str(report_dir),
        "cities": cities,
        "categories": categories,
    }


def cmd_run(args: argparse.Namespace) -> int:
    """Interactive run command."""
    console.print(Panel.fit("[bold green]Client Acquisition System[/bold green]"))

    city_input = Prompt.ask("Which city/cities to focus on? (comma-separated for multiple)")
    cities = [c.strip() for c in city_input.split(",") if c.strip()]
    if not cities:
        console.print("[red]At least one city required.[/red]")
        return 1

    category_input = Prompt.ask(
        "What business type(s)? (comma-separated, e.g., cafe,salon,retail)"
    )
    categories = [c.strip() for c in category_input.split(",") if c.strip()]
    if not categories:
        categories = ["all"]

    max_leads = IntPrompt.ask("How many leads per city+category combo?", default=20)

    db = get_db()
    for city in cities:
        stats = get_city_summary(db, city)
        if stats["contacted"] > 0:
            if not Confirm.ask(
                f"You already contacted {stats['contacted']} businesses in {city}. Skip them?",
                default=True,
            ):
                db.close()
                return 0
    db.close()

    channels = []
    if Confirm.ask("Send via Email?", default=True):
        channels.append("email")
    if Confirm.ask("Send via WhatsApp?", default=False):
        channels.append("whatsapp")

    if not channels:
        console.print("[yellow]No channels selected. Exiting.[/yellow]")
        return 0

    if len(cities) == 1 and len(categories) == 1:
        result = run_pipeline(cities[0], categories[0], max_leads, skip_contacted=True, channels=channels)
    else:
        result = run_multi_pipeline(
            cities=cities,
            categories=categories,
            max_leads_per_combo=max_leads,
            skip_contacted=True,
            channels=channels,
        )
    if "error" in result:
        return 1
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    """Batch run command for headless operation."""
    console.print(Panel.fit("[bold green]Batch Client Acquisition[/bold green]"))

    cities = [c.strip() for c in args.cities.split(",") if c.strip()]
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    if not cities or not categories:
        console.print("[red]--cities and --categories are required.[/red]")
        return 1

    result = run_multi_pipeline(
        cities=cities,
        categories=categories,
        max_leads_per_combo=args.max_leads,
        skip_contacted=not args.no_skip,
        channels=args.channels.split(",") if args.channels else ["email"],
        auto_send=args.auto_send,
        enable_follow_up=not args.no_follow_up,
        require_both_contacts=args.require_both_contacts,
    )
    if "error" in result:
        return 1
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """Show summary for a city or all cities."""
    db = get_db()
    summarizer = Summarizer()
    if args.city:
        summarizer.city_summary(db, args.city)
    else:
        summarizer.all_cities_summary(db)
    db.close()
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Start the dashboard server."""
    settings = get_settings()
    console.print(f"[green]Starting dashboard at http://127.0.0.1:{settings.dashboard_port}[/green]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")
    start_dashboard()
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    """Reset outreach statuses for a city."""
    if not args.city:
        console.print("[red]--city is required for reset.[/red]")
        return 1

    db = get_db()
    leads = db.query(Lead).filter(Lead.city.ilike(args.city)).all()
    if not leads:
        console.print(f"[yellow]No leads found in {args.city}.[/yellow]")
        db.close()
        return 0

    count = 0
    for lead in leads:
        for outreach in lead.outreaches:
            outreach.status = OutreachStatus.PENDING
            outreach.sent_at = None
            count += 1
    db.commit()
    db.close()
    console.print(f"[green]Reset {count} outreach records in {args.city}.[/green]")
    return 0


def cmd_hot_leads(args: argparse.Namespace) -> int:
    """Show hot leads sorted by score."""
    db = get_db()
    leads = get_hot_leads(db, min_score=args.min_score, limit=args.limit)
    if not leads:
        console.print("[yellow]No hot leads found.[/yellow]")
        db.close()
        return 0

    from rich.table import Table
    table = Table(title=f"Hot Leads (Score >= {args.min_score})")
    table.add_column("Business", style="cyan")
    table.add_column("City", style="dim")
    table.add_column("Type", style="magenta")
    table.add_column("Score", style="green")
    table.add_column("Stage", style="yellow")
    table.add_column("Maturity", style="blue")

    for lead in leads:
        table.add_row(
            lead.business_name,
            lead.city,
            lead.business_type,
            str(lead.lead_score or 0),
            lead.kanban_stage or "cold",
            lead.maturity_stage or "N/A",
        )
    console.print(table)
    db.close()
    return 0


def cmd_process_follow_ups(args: argparse.Namespace) -> int:
    """Process pending follow-ups that are due."""
    from datetime import datetime, timezone
    from src.follow_up import FollowUpEngine
    from src.messenger import EmailSender, WhatsAppSender

    db = get_db()
    engine = FollowUpEngine()
    pending = engine.get_pending_follow_ups(db)

    if not pending:
        console.print("[yellow]No follow-ups due.[/yellow]")
        db.close()
        return 0

    console.print(f"[bold]{len(pending)} follow-ups due.[/bold]")

    email_sender = EmailSender()
    wa_sender = WhatsAppSender()
    sent = 0
    failed = 0

    for fu in pending:
        lead = fu.lead
        try:
            if fu.channel == OutreachChannel.EMAIL and lead.email:
                email_sender.send(lead.email, f"Following up — {lead.business_name}", fu.message_text)
                fu.status = OutreachStatus.SENT
                fu.sent_at = datetime.now(timezone.utc)
                sent += 1
                console.print(f"[green]✓ Follow-up email to {lead.business_name}[/green]")
            elif fu.channel == OutreachChannel.WHATSAPP and lead.phone:
                if wa_sender.ensure_auth():
                    wa_sender.send(lead.phone, fu.message_text)
                    fu.status = OutreachStatus.SENT
                    fu.sent_at = datetime.now(timezone.utc)
                    sent += 1
                    console.print(f"[green]✓ Follow-up WhatsApp to {lead.business_name}[/green]")
                else:
                    raise WhatsAppError("Not authenticated")
            else:
                fu.status = OutreachStatus.FAILED
                fu.error_message = "No contact info"
                failed += 1
        except Exception as exc:
            fu.status = OutreachStatus.FAILED
            fu.error_message = str(exc)[:500]
            failed += 1
            console.print(f"[red]✗ Follow-up failed for {lead.business_name}: {exc}[/red]")

    db.commit()
    wa_sender.close()
    db.close()
    console.print(f"[bold]Done:[/bold] {sent} sent, {failed} failed.")
    return 0


def cmd_reports(args: argparse.Namespace) -> int:
    """List available daily reports."""
    dates = list_report_dates()
    if not dates:
        console.print("[yellow]No reports found yet.[/yellow]")
        return 0

    from rich.table import Table
    table = Table(title="Daily Reports")
    table.add_column("Date", style="cyan")
    table.add_column("Path", style="dim")

    for d in dates:
        table.add_row(d, str(Path("reports") / d))
    console.print(table)
    return 0


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Client Acquisition System")
    subparsers = parser.add_subparsers(dest="command")

    # run
    run_parser = subparsers.add_parser("run", help="Interactive pipeline")
    run_parser.set_defaults(func=cmd_run)

    # batch
    batch_parser = subparsers.add_parser("batch", help="Batch pipeline (headless, multi-city)")
    batch_parser.add_argument("--cities", required=True, help="Comma-separated city names")
    batch_parser.add_argument("--categories", default="all", help="Comma-separated categories")
    batch_parser.add_argument("--max-leads", type=int, default=50, help="Max leads per city+category")
    batch_parser.add_argument("--channels", default="email", help="Comma-separated channels")
    batch_parser.add_argument("--auto-send", action="store_true", help="Auto-send without prompting")
    batch_parser.add_argument("--no-skip", action="store_true", help="Don't skip already contacted")
    batch_parser.add_argument("--no-follow-up", action="store_true", help="Disable follow-up scheduling")
    batch_parser.add_argument("--require-both-contacts", action="store_true", help="Only process leads with both email and phone")
    batch_parser.set_defaults(func=cmd_batch)

    # summary
    sum_parser = subparsers.add_parser("summary", help="Show summary report")
    sum_parser.add_argument("--city", help="City name")
    sum_parser.set_defaults(func=cmd_summary)

    # dashboard
    dash_parser = subparsers.add_parser("dashboard", help="Start web dashboard")
    dash_parser.set_defaults(func=cmd_dashboard)

    # reset
    reset_parser = subparsers.add_parser("reset", help="Reset outreach statuses for a city")
    reset_parser.add_argument("--city", required=True, help="City name")
    reset_parser.set_defaults(func=cmd_reset)

    # hot-leads
    hot_parser = subparsers.add_parser("hot-leads", help="Show high-scoring leads")
    hot_parser.add_argument("--min-score", type=int, default=70, help="Minimum lead score")
    hot_parser.add_argument("--limit", type=int, default=50, help="Max results")
    hot_parser.set_defaults(func=cmd_hot_leads)

    # follow-ups
    fu_parser = subparsers.add_parser("follow-ups", help="Process pending follow-ups")
    fu_parser.set_defaults(func=cmd_process_follow_ups)

    # reports
    reports_parser = subparsers.add_parser("reports", help="List daily reports")
    reports_parser.set_defaults(func=cmd_reports)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
