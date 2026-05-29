"""Tests for main CLI module."""

from unittest.mock import MagicMock, patch

import pytest

from src.discovery import DiscoveryError
from src.main import run_pipeline


class TestRunPipeline:
    """Test suite for run_pipeline orchestration."""

    def test_pipeline_returns_error_on_discovery_failure(self) -> None:
        """Should return error dict when discovery fails."""
        with patch("src.main.WebsiteVerifier") as MockVerifier:
            MockVerifier.return_value.verify.return_value = {"has_real_website": False}
            with patch("src.main.GoogleMapsScraper") as MockScraper:
                mock_scraper = MagicMock()
                mock_scraper.discover.side_effect = DiscoveryError("Maps error")
                MockScraper.return_value = mock_scraper
                with patch("src.main.init_db"):
                    with patch("src.main.get_sessionmaker"):
                        with patch("src.main.get_city_summary", return_value={
                            "total": 0, "contacted": 0, "failed": 0, "pending": 0, "responded": 0
                        }):
                            from sqlalchemy.orm import sessionmaker
                            from sqlalchemy import create_engine
                            from src.models import Base
                            engine = create_engine("sqlite:///:memory:")
                            Base.metadata.create_all(engine)
                            Session = sessionmaker(bind=engine)
                            with patch("src.main.get_db", return_value=Session()):
                                result = run_pipeline("Mumbai", "cafe", 5, skip_contacted=True, channels=[])
        assert isinstance(result, dict)

    def test_pipeline_skips_real_website(self) -> None:
        """Leads with a real business website (.com, .in, etc.) should be skipped."""
        from src.researcher import WebsiteResearcher
        with patch("src.main.WebsiteVerifier") as MockVerifier:
            MockVerifier.return_value.verify.return_value = {"has_real_website": False}
            mock_lead = {
                "business_name": "Modern Cafe",
                "address": "A road",
                "phone": None,
                "email": None,
                "website": "https://modern-cafe.com",
                "google_maps_url": "https://maps.example.com/1",
                "city": "Mumbai",
                "business_type": "cafe",
            }
            with patch("src.main.GoogleMapsScraper") as MockScraper:
                mock_scraper = MagicMock()
                mock_scraper.discover.return_value = [mock_lead]
                MockScraper.return_value = mock_scraper
                with patch.object(WebsiteResearcher, "research", return_value={"pitch_text": "mock"}):
                    with patch("src.main.init_db"):
                        with patch("src.main.get_sessionmaker"):
                            with patch("src.main.get_city_summary", return_value={
                                "total": 0, "contacted": 0, "failed": 0, "pending": 0, "responded": 0
                            }):
                                from sqlalchemy.orm import sessionmaker
                                from sqlalchemy import create_engine
                                from src.models import Base
                                engine = create_engine("sqlite:///:memory:")
                                Base.metadata.create_all(engine)
                                Session = sessionmaker(bind=engine)
                                with patch("src.main.get_db", return_value=Session()):
                                    with patch("src.main.Prompt.ask", return_value="s"):
                                        result = run_pipeline("Mumbai", "cafe", 5, skip_contacted=True, channels=[])
        assert isinstance(result, dict)
        assert result.get("found", 0) == 0

    def test_pipeline_keeps_social_media_link(self) -> None:
        """Leads with only a social media link (no real website) should proceed."""
        from src.researcher import WebsiteResearcher
        with patch("src.main.WebsiteVerifier") as MockVerifier:
            MockVerifier.return_value.verify.return_value = {"has_real_website": False}
            mock_lead = {
                "business_name": "Insta Cafe",
                "address": "B road",
                "phone": None,
                "email": "insta@cafe.com",
                "website": "https://instagram.com/instacafe",
                "google_maps_url": "https://maps.example.com/2",
                "city": "Mumbai",
                "business_type": "cafe",
            }
            with patch("src.main.GoogleMapsScraper") as MockScraper:
                mock_scraper = MagicMock()
                mock_scraper.discover.return_value = [mock_lead]
                MockScraper.return_value = mock_scraper
                with patch.object(WebsiteResearcher, "research", return_value={"pitch_text": "mock"}):
                    with patch("src.main.init_db"):
                        with patch("src.main.get_sessionmaker"):
                            with patch("src.main.get_city_summary", return_value={
                                "total": 0, "contacted": 0, "failed": 0, "pending": 0, "responded": 0
                            }):
                                from sqlalchemy.orm import sessionmaker
                                from sqlalchemy import create_engine
                                from src.models import Base
                                engine = create_engine("sqlite:///:memory:")
                                Base.metadata.create_all(engine)
                                Session = sessionmaker(bind=engine)
                                with patch("src.main.get_db", return_value=Session()):
                                    with patch("src.main.Prompt.ask", return_value="s"):
                                        result = run_pipeline("Mumbai", "cafe", 5, skip_contacted=True, channels=[])
        assert isinstance(result, dict)
        # Social media link is treated as "no real website", so lead is kept
        assert result.get("found", 0) == 1

    def test_pipeline_keeps_no_website(self) -> None:
        """Leads with no website at all should proceed."""
        from src.researcher import WebsiteResearcher
        with patch("src.main.WebsiteVerifier") as MockVerifier:
            MockVerifier.return_value.verify.return_value = {"has_real_website": False}
            mock_lead = {
                "business_name": "NoSite Cafe",
                "address": "C road",
                "phone": None,
                "email": "nosite@cafe.com",
                "website": None,
                "google_maps_url": "https://maps.example.com/3",
                "city": "Mumbai",
                "business_type": "cafe",
            }
            with patch("src.main.GoogleMapsScraper") as MockScraper:
                mock_scraper = MagicMock()
                mock_scraper.discover.return_value = [mock_lead]
                MockScraper.return_value = mock_scraper
                with patch.object(WebsiteResearcher, "research", return_value={"pitch_text": "mock"}):
                    with patch("src.main.init_db"):
                        with patch("src.main.get_sessionmaker"):
                            with patch("src.main.get_city_summary", return_value={
                                "total": 0, "contacted": 0, "failed": 0, "pending": 0, "responded": 0
                            }):
                                from sqlalchemy.orm import sessionmaker
                                from sqlalchemy import create_engine
                                from src.models import Base
                                engine = create_engine("sqlite:///:memory:")
                                Base.metadata.create_all(engine)
                                Session = sessionmaker(bind=engine)
                                with patch("src.main.get_db", return_value=Session()):
                                    with patch("src.main.Prompt.ask", return_value="s"):
                                        result = run_pipeline("Mumbai", "cafe", 5, skip_contacted=True, channels=[])
        assert isinstance(result, dict)
        assert result.get("found", 0) == 1

    def test_pipeline_skips_when_verifier_finds_website(self) -> None:
        """When Google Maps shows no website but online search finds one, skip."""
        from src.researcher import WebsiteResearcher
        with patch("src.main.WebsiteVerifier") as MockVerifier:
            MockVerifier.return_value.verify.return_value = {
                "has_real_website": True,
                "found_url": "https://hidden-website.com",
            }
            mock_lead = {
                "business_name": "Secret Cafe",
                "address": "D road",
                "phone": None,
                "email": "secret@cafe.com",
                "website": None,
                "google_maps_url": "https://maps.example.com/4",
                "city": "Mumbai",
                "business_type": "cafe",
            }
            with patch("src.main.GoogleMapsScraper") as MockScraper:
                mock_scraper = MagicMock()
                mock_scraper.discover.return_value = [mock_lead]
                MockScraper.return_value = mock_scraper
                with patch.object(WebsiteResearcher, "research", return_value={"pitch_text": "mock"}):
                    with patch("src.main.init_db"):
                        with patch("src.main.get_sessionmaker"):
                            with patch("src.main.get_city_summary", return_value={
                                "total": 0, "contacted": 0, "failed": 0, "pending": 0, "responded": 0
                            }):
                                from sqlalchemy.orm import sessionmaker
                                from sqlalchemy import create_engine
                                from src.models import Base
                                engine = create_engine("sqlite:///:memory:")
                                Base.metadata.create_all(engine)
                                Session = sessionmaker(bind=engine)
                                with patch("src.main.get_db", return_value=Session()):
                                    with patch("src.main.Prompt.ask", return_value="s"):
                                        result = run_pipeline("Mumbai", "cafe", 5, skip_contacted=True, channels=[])
        assert isinstance(result, dict)
        assert result.get("found", 0) == 0
