"""Database engine and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import get_settings
from src.models import Base


def get_engine(db_uri: str | None = None):
    """Create SQLAlchemy engine.

    Supports both SQLite (default) and PostgreSQL via configuration.
    """
    if db_uri is None:
        settings = get_settings()
        if settings.use_postgres and settings.database_url:
            return create_engine(
                settings.database_url, echo=False, future=True, pool_pre_ping=True
            )
        db_uri = settings.db_uri
    return create_engine(db_uri, echo=False, future=True)


def get_sessionmaker(engine):
    """Return a sessionmaker bound to engine."""
    return sessionmaker(bind=engine)


def init_db(db_uri: str | None = None):
    """Create all tables."""
    engine = get_engine(db_uri)
    Base.metadata.create_all(engine)
    return engine


def get_db():
    """Yield a DB session (generator for FastAPI dependency)."""
    engine = get_engine()
    SessionLocal = get_sessionmaker(engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
