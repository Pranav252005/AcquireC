"""Tests for daily reports module."""

from unittest.mock import MagicMock

from src.reports import DailySummary, _today_dir, list_report_dates, save_daily_report


class TestTodayDir:
    def test_creates_directories(self, tmp_path) -> None:
        import src.reports as reports_mod
        original_dir = reports_mod.REPORTS_DIR
        try:
            reports_mod.REPORTS_DIR = tmp_path / "reports"
            path = _today_dir()
            assert path.exists()
            assert (path / "by-city").exists()
            assert (path / "by-category").exists()
            assert (path / "by-contact").exists()
        finally:
            reports_mod.REPORTS_DIR = original_dir


class TestSaveDailyReport:
    def test_saves_summary_and_csvs(self, tmp_path) -> None:
        import src.reports as reports_mod
        original_dir = reports_mod.REPORTS_DIR
        try:
            reports_mod.REPORTS_DIR = tmp_path / "reports"
            db = MagicMock()
            lead1 = MagicMock()
            lead1.business_name = "Test Cafe"
            lead1.city = "Mumbai"
            lead1.business_type = "cafe"
            lead1.address = "Main St"
            lead1.phone = "+91 98765 43210"
            lead1.email = "test@cafe.com"
            lead1.website = "http://testcafe.com"
            lead1.google_maps_url = ""
            lead1.rating = 4.5
            lead1.review_count = 120
            lead1.price_level = "$$"
            lead1.years_in_business = 5
            lead1.maturity_stage = "growth"
            lead1.lead_score = 85
            lead1.kanban_stage = "pitched"
            lead1.membership_idea = "Regulars Club"
            lead1.created_at = None
            lead1.outreaches = []

            lead2 = MagicMock()
            lead2.business_name = "Test Salon"
            lead2.city = "Delhi"
            lead2.business_type = "salon"
            lead2.address = "High St"
            lead2.phone = "+91 98765 43211"
            lead2.email = None
            lead2.website = None
            lead2.google_maps_url = ""
            lead2.rating = None
            lead2.review_count = None
            lead2.price_level = None
            lead2.years_in_business = None
            lead2.maturity_stage = None
            lead2.lead_score = None
            lead2.kanban_stage = "cold"
            lead2.membership_idea = None
            lead2.created_at = None
            lead2.outreaches = []

            report_dir = save_daily_report(
                db=db,
                discovered_leads=[
                    {"business_name": "Test Cafe", "city": "Mumbai", "category": "cafe"},
                    {"business_name": "Test Salon", "city": "Delhi", "category": "salon"},
                ],
                processed_leads=[lead1, lead2],
                sent=1,
                failed=0,
                skipped=0,
                cities=["Mumbai", "Delhi"],
                categories=["cafe", "salon"],
            )

            assert report_dir.exists()
            assert (report_dir / "leads.csv").exists()
            assert (report_dir / "by-contact" / "with_both.csv").exists()
            assert (report_dir / "by-contact" / "phone_only.csv").exists()
            assert (report_dir / "by-city" / "Mumbai.csv").exists()
            assert (report_dir / "by-city" / "Delhi.csv").exists()
            assert (report_dir / "by-category" / "cafe.csv").exists()
            assert (report_dir / "by-category" / "salon.csv").exists()

            # Check summary text was generated
            summaries = list(report_dir.glob("summary_*.txt"))
            assert len(summaries) == 1
            text = summaries[0].read_text(encoding="utf-8")
            assert "Test Cafe" not in text  # summary is aggregate stats
            assert "Mumbai" in text
            assert "cafe" in text
        finally:
            reports_mod.REPORTS_DIR = original_dir


class TestListReportDates:
    def test_empty_when_no_reports(self, tmp_path) -> None:
        import src.reports as reports_mod
        original_dir = reports_mod.REPORTS_DIR
        try:
            reports_mod.REPORTS_DIR = tmp_path / "empty_reports"
            assert list_report_dates() == []
        finally:
            reports_mod.REPORTS_DIR = original_dir
