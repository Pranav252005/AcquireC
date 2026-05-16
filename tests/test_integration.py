"""Integration test for the full pipeline."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import init_db
from src.models import Base, Lead, Outreach, OutreachChannel, OutreachStatus
from src.tracker import get_or_create_lead, log_outreach, is_already_contacted, get_city_summary


class TestIntegration:
    """End-to-end integration test."""

    def test_full_pipeline_simulation(self, tmp_path) -> None:
        """Simulate discovery, dedup, outreach, and summary."""
        db_file = tmp_path / "integration.db"
        engine = init_db(f"sqlite:///{db_file}")
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        db = Session()

        # Step 1: Simulate discovery — add 2 leads
        l1_data = {
            "city": "Pune",
            "business_name": "Cafe Alpha",
            "business_type": "cafe",
            "address": "123 Main Rd",
            "phone": "+911111111111",
            "email": "alpha@cafe.com",
            "google_maps_url": "https://maps.example.com/1",
        }
        l2_data = {
            "city": "Pune",
            "business_name": "Salon Beta",
            "business_type": "salon",
            "address": "456 Side St",
            "phone": "+912222222222",
            "google_maps_url": "https://maps.example.com/2",
        }

        lead1 = get_or_create_lead(db, "Pune", "Cafe Alpha", defaults=l1_data)
        lead2 = get_or_create_lead(db, "Pune", "Salon Beta", defaults=l2_data)

        assert lead1.id is not None
        assert lead2.id is not None

        # Step 2: Simulate dedup — same lead should not duplicate
        lead1_again = get_or_create_lead(db, "Pune", "Cafe Alpha", defaults=l1_data)
        assert lead1_again.id == lead1.id

        # Step 3: Log outreach
        log_outreach(
            db, lead1.id, OutreachChannel.EMAIL,
            "Hi, we build websites...", "Initial pitch for Cafe Alpha",
            status=OutreachStatus.SENT,
        )
        log_outreach(
            db, lead2.id, OutreachChannel.WHATSAPP,
            "Hi Salon Beta...", "Salon pitch",
            status=OutreachStatus.FAILED,
            error_message="Invalid phone",
        )

        # Step 4: Verify dedup
        assert is_already_contacted(db, "Pune", "Cafe Alpha") is True
        assert is_already_contacted(db, "Pune", "Salon Beta") is False  # failed only

        # Step 5: Verify summary
        summary = get_city_summary(db, "Pune")
        assert summary["total"] == 2
        assert summary["contacted"] == 1
        assert summary["failed"] == 1
        assert summary["responded"] == 0

        db.close()
