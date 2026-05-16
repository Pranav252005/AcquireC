"""Pytest fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import init_db
from src.models import Base


@pytest.fixture
def temp_db(tmp_path):
    """Create a fresh SQLite DB per test."""
    db_file = tmp_path / "test.db"
    engine = init_db(f"sqlite:///{db_file}")
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    yield db
    db.close()


@pytest.fixture
def mock_playwright(mocker):
    """Provide a mocked Playwright browser/context/page chain."""
    mock_page = mocker.MagicMock()
    mock_context = mocker.MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = mocker.MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_playwright = mocker.MagicMock()
    mock_playwright.chromium.launch.return_value = mock_browser

    return {
        "playwright": mock_playwright,
        "browser": mock_browser,
        "context": mock_context,
        "page": mock_page,
    }
