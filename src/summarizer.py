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

    def city_summary(self, db: Session, city: str) -> str:
        """Return a formatted city summary as string."""
        stats = get_city_summary(db, city)
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
        cities = get_all_cities(db)
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
        lead = get_lead_detail(db, lead_id)
        if not lead:
            self.console.print("[red]Lead not found.[/red]")
            return "Not found"

        self.console.print(f"\n[bold]{lead.business_name}[/bold] — {lead.city}")
        self.console.print(f"Type: {lead.business_type}")
        self.console.print(f"Address: {lead.address}")
        self.console.print(f"Phone: {lead.phone or 'N/A'}")
        self.console.print(f"Email: {lead.email or 'N/A'}")
        self.console.print(f"Website: {lead.website or 'N/A'}")
        self.console.print(f"LinkedIn: {lead.linkedin_url or 'N/A'}")
        self.console.print(f"Years in business: {lead.years_in_business or 'Unknown'}")
        self.console.print(f"Summary: {lead.linkedin_summary or 'N/A'}")

        if lead.outreaches:
            self.console.print("\n[bold]Outreach History:[/bold]")
            for o in lead.outreaches:
                status_color = {
                    OutreachStatus.SENT: "green",
                    OutreachStatus.FAILED: "red",
                    OutreachStatus.PENDING: "yellow",
                    OutreachStatus.RESPONDED: "blue",
                }.get(o.status, "white")
                self.console.print(
                    f"  [{status_color}]{o.channel.value.upper()} — {o.status.value}[/{status_color}] "
                    f"({o.sent_at or 'not sent'})"
                )
                self.console.print(f"    Context: {o.context_summary}")
                self.console.print(f"    Message: {o.message_text[:200]}...")
        else:
            self.console.print("\n[yellow]No outreach attempts yet.[/yellow]")

        return f"Detail for lead {lead_id}"
