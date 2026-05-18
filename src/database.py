"""Database engine and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings
from src.models import AppConfig, Base


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
    """Create all tables and seed AppConfig from .env if empty."""
    engine = get_engine(db_uri)
    Base.metadata.create_all(engine)
    with Session(bind=engine) as seed_session:
        if not seed_session.query(AppConfig).first():
            s = get_settings()
            defaults = [
                ("local_model_path", s.local_model_path),
                ("vlm_model_dir", s.vlm_model_dir),
                ("vlm_model_file", s.vlm_model_file),
                ("vlm_mmproj_file", s.vlm_mmproj_file),
                ("llm_provider", s.llm_provider),
                ("openai_api_key", s.openai_api_key),
                ("anthropic_api_key", s.anthropic_api_key),
                ("ollama_url", s.ollama_url),
                ("ollama_model", s.ollama_model),
            ]
            for k, v in defaults:
                seed_session.add(AppConfig(key=k, value=v))
            seed_session.commit()
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


def get_app_config(db: Session, key: str, default: str | None = None) -> str | None:
    """Return a runtime config value from the DB, or *default* if missing."""
    row = db.query(AppConfig).filter_by(key=key).first()
    return row.value if row else default


def set_app_config(db: Session, key: str, value: str | None) -> None:
    """Upsert a runtime config value in the DB."""
    row = db.query(AppConfig).filter_by(key=key).first()
    if row:
        row.value = value
    else:
        row = AppConfig(key=key, value=value)
        db.add(row)
    db.commit()
