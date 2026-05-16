"""Summary reports for leads and cities."""

from typing import Any

from rich.console import Console
from rich.table import Table
from sqlalchemy.orm import Session

from src.models import Lead, Outreach, OutreachStatus
from src.tracker import get_all_cities, get_city_summary, get_lead_detail


class Summarizer:
    """Generate CLI-friendly summary reports."""

    def __init__(self) -> None:
        self.console = Console()

    # ------------------------------------------------------------------ #
    # Data-only methods (no side effects)
    # ------------------------------------------------------------------ #

    def city_summary_data(self, db: Session, city: str) -> dict[str, Any]:
        """Return raw city summary data."""
        return get_city_summary(db, city)

    def all_cities_summary_data(self, db: Session) -> list[dict[str, Any]]:
        """Return raw data for all cities."""
        return get_all_cities(db)

    def lead_detail_data(self, db: Session, lead_id: int) -> dict[str, Any] | None:
        """Return detailed lead data as a dict, or None if not found."""
        lead = get_lead_detail(db, lead_id)
        if not lead:
            return None
        outreaches = []
        for o in lead.outreaches:
            outreaches.append({
                "channel": o.channel.value,
                "status": o.status.value,
                "sent_at": str(o.sent_at) if o.sent_at else None,
                "context_summary": o.context_summary,
                "message_text": o.message_text,
            })
        return {
            "business_name": lead.business_name,
            "city": lead.city,
            "business_type": lead.business_type,
            "address": lead.address,
            "phone": lead.phone,
            "email": lead.email,
            "website": lead.website,
            "years_in_business": lead.years_in_business,
            "outreaches": outreaches,
        }

    # ------------------------------------------------------------------ #
    # Presentation methods (print to console)
    # ------------------------------------------------------------------ #

    def city_summary(self, db: Session, city: str) -> str:
        """Return a formatted city summary as string."""
        stats = self.city_summary_data(db, city)
        table = Table(title=f"City Summary: {city}")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_row("Total Leads", str(stats["total"]))
        table.add_row("Contacted (Sent)", str(stats["contacted"]))
        table.add_row("Pending", str(stats["pending"]))
        table.add_row("Failed", str(stats["failed"]))
        table.add_row("Responded", str(stats["responded"]))
        self.console.print(table)
        return f"Summary for {city}: {stats}"

    def all_cities_summary(self, db: Session) -> str:
        """Return a formatted summary of all cities."""
        cities = self.all_cities_summary_data(db)
        if not cities:
            self.console.print("[yellow]No cities found yet.[/yellow]")
            return "No data"

        table = Table(title="All Cities Summary")
        table.add_column("City", style="cyan")
        table.add_column("Total", style="magenta")
        table.add_column("Sent", style="green")
        table.add_column("Failed", style="red")
        table.add_column("Responded", style="blue")

        for row in cities:
            table.add_row(
                row["city"],
                str(row["total"]),
                str(row["contacted"]),
                str(row["failed"]),
                str(row["responded"]),
            )
        self.console.print(table)
        return f"Found {len(cities)} cities"

    def lead_detail_report(self, db: Session, lead_id: int) -> str:
        """Return detailed info for a single lead."""
        data = self.lead_detail_data(db, lead_id)
        if data is None:
            self.console.print("[red]Lead not found.[/red]")
            return "Not found"

        self.console.print(f"\n[bold]{data['business_name']}[/bold] — {data['city']}")
        self.console.print(f"Type: {data['business_type']}")
        self.console.print(f"Address: {data['address']}")
        self.console.print(f"Phone: {data['phone'] or 'N/A'}")
        self.console.print(f"Email: {data['email'] or 'N/A'}")
        self.console.print(f"Website: {data['website'] or 'N/A'}")
        self.console.print(f"Years in business: {data['years_in_business'] or 'Unknown'}")

        if data["outreaches"]:
            self.console.print("\n[bold]Outreach History:[/bold]")
            for o in data["outreaches"]:
                status_color = {
                    "sent": "green",
                    "failed": "red",
                    "pending": "yellow",
                    "responded": "blue",
                    "cancelled": "dim",
                }.get(o["status"], "white")
                self.console.print(
                    f"  [{status_color}]{o['channel'].upper()} — {o['status']}[/{status_color}] "
                    f"({o['sent_at'] or 'not sent'})"
                )
                self.console.print(f"    Context: {o['context_summary']}")
                self.console.print(f"    Message: {o['message_text'][:200]}...")
        else:
            self.console.print("\n[yellow]No outreach attempts yet.[/yellow]")

        return f"Detail for lead {lead_id}"
