"""Database engine and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import get_settings
from src.models import Base


def get_engine(db_uri: str | None = None):
    """Create SQLAlchemy engine."""
    if db_uri is None:
        db_uri = get_settings().db_uri
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
