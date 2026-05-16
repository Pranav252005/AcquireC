"""Tests for dashboard module."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.dashboard import app, get_db
from src.database import init_db
from src.models import Lead, Outreach, OutreachChannel, OutreachStatus
from src.tracker import get_or_create_lead, log_outreach


def _make_override(db_uri: str):
    """Factory for DB dependency overrides."""
    engine = init_db(db_uri)
    Session = sessionmaker(bind=engine)

    def _override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    return _override_get_db


class TestDashboard:
    """Test suite for FastAPI dashboard."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Override DB dependency to use temp file."""
        db_file = tmp_path / "dash.db"
        override = _make_override(f"sqlite:///{db_file}")
        app.dependency_overrides[get_db] = override
        yield
        app.dependency_overrides.clear()

    def test_index_returns_200(self) -> None:
        """GET / should return HTML."""
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "Dashboard" in response.text

    def test_api_stats_returns_json(self) -> None:
        """GET /api/stats should return JSON with stats."""
        client = TestClient(app)
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert data["total"] == 0

    def test_leads_page(self) -> None:
        """GET /leads should return HTML."""
        client = TestClient(app)
        response = client.get("/leads")
        assert response.status_code == 200
        assert "Leads" in response.text

    def test_city_report(self) -> None:
        """GET /cities/{city} should return HTML."""
        client = TestClient(app)
        response = client.get("/cities/Mumbai")
        assert response.status_code == 200
        assert "Mumbai" in response.text
