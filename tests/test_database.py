"""Tests for database module."""

from sqlalchemy import inspect

from src.database import get_engine, get_sessionmaker, init_db
from src.models import Base, Lead


class TestDatabase:
    """Test suite for database setup."""

    def test_init_db_creates_tables(self, tmp_path) -> None:
        """init_db should create all tables in sqlite file."""
        db_file = tmp_path / "test.db"
        engine = init_db(f"sqlite:///{db_file}")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "leads" in tables
        assert "outreaches" in tables

    def test_get_engine_returns_engine(self, tmp_path) -> None:
        """get_engine should return a SQLAlchemy engine."""
        db_file = tmp_path / "test2.db"
        engine = get_engine(f"sqlite:///{db_file}")
        from sqlalchemy.engine import Engine
        assert isinstance(engine, Engine)

    def test_session_crud(self, tmp_path) -> None:
        """Session should support basic CRUD."""
        db_file = tmp_path / "test3.db"
        engine = init_db(f"sqlite:///{db_file}")
        Session = get_sessionmaker(engine)
        with Session() as session:
            lead = Lead(
                city="Pune",
                business_name="Beta Salon",
                business_type="salon",
                address="45 Road",
                google_maps_url="https://maps.example.com/2",
            )
            session.add(lead)
            session.commit()
            assert lead.id is not None

        with Session() as session:
            result = session.query(Lead).filter_by(city="Pune").first()
            assert result is not None
            assert result.business_name == "Beta Salon"
