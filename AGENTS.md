# AGENTS.md — Client Acquisition System

> This file is for AI coding agents. It describes the project architecture, conventions, and workflows. Assume the reader knows nothing about the project.

---

## Project Overview

The **Client Acquisition System** is a Python application that automates local business outreach:

1. **Discover** — Scrape Google Maps for business listings by city and category.
2. **Audit** — Evaluate the business's existing website for quality signals (mobile, speed, old tech).
3. **Research** — Enrich leads with LinkedIn data.
4. **Generate Pitch** — Use a local Vision-Language Model (VLM) to write personalized website-development pitches.
5. **Outreach** — Send pitches via SMTP Email or WhatsApp Web.
6. **Track** — Store everything in SQLite; browse via a FastAPI dashboard.

The project uses a **multi-layer browser automation stack**: direct Playwright selectors → accessibility-tree mapping → vision-guided agent (screenshot + local VLM) as final fallback.

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| Browser Automation | Playwright (sync API) |
| Database | SQLite + SQLAlchemy 2.0 (ORM) |
| Web Dashboard | FastAPI + Jinja2 + TailwindCSS (CDN) + Chart.js (CDN) |
| CLI UI | Rich (tables, prompts, progress spinners) |
| Local AI | llama-cpp-python (Qwen 3.5 9B GGUF) |
| Config | Pydantic Settings (`.env` file) |
| Testing | pytest + pytest-mock (via `pytest-mock` or `unittest.mock`) |

### External Prerequisites

- **Chromium** — installed via `playwright install chromium`
- **Local VLM weights** — GGUF + mmproj files at the path configured in `.env` (default: `/home/pranavvv/models/qwen3.5-VLM-9b/`)

---

## Directory Layout

```
acquire_clients/
├── src/                          # Application code (package root)
│   ├── __init__.py
│   ├── config.py                 # Pydantic Settings from .env
│   ├── models.py                 # SQLAlchemy ORM models (Lead, Outreach)
│   ├── database.py               # Engine, sessionmaker, init_db
│   ├── tracker.py                # Deduplication, outreach logging, summaries
│   ├── discovery.py              # GoogleMapsScraper (Playwright)
│   ├── researcher.py             # LinkedInResearcher + AI pitch generation
│   ├── messenger.py              # EmailSender (SMTP) + WhatsAppSender (Web)
│   ├── summarizer.py             # Rich CLI tables and reports
│   ├── dashboard.py              # FastAPI app + Jinja2 templates
│   ├── website_auditor.py        # Website quality audit
│   ├── main.py                   # CLI entry point (argparse)
│   ├── vision_agent.py           # Perceive-plan-act browser agent
│   ├── vision_engine.py          # Screenshots, annotation, VLM inference
│   ├── vision_executor.py        # Execute VLM actions on Playwright page
│   ├── vision_mapper.py          # Accessibility-tree element discovery
│   └── templates/                # Jinja2 HTML templates
│       ├── base.html
│       ├── index.html
│       ├── leads.html
│       ├── lead_detail.html
│       ├── city_report.html
│       ├── drafts.html
│       └── draft_detail.html
├── tests/                        # pytest suite
│   ├── conftest.py               # Fixtures: temp_db, mock_playwright
│   ├── test_config.py
│   ├── test_dashboard.py
│   ├── test_database.py
│   ├── test_discovery.py
│   ├── test_integration.py
│   ├── test_main.py
│   ├── test_messenger.py
│   ├── test_models.py
│   ├── test_researcher.py
│   ├── test_summarizer.py
│   ├── test_tracker.py
│   ├── test_vision_engine.py
│   ├── test_vision_executor.py
│   └── test_website_auditor.py
├── data/                         # SQLite DB + WhatsApp drafts
│   ├── leads.db
│   └── whatsapp_drafts/
├── whatsapp_session/             # Persistent WhatsApp Web session data
├── screenshots/                  # Debug screenshots (auto-created)
├── requirements.txt
├── .env.example
└── .env                          # Not committed; copy from .env.example
```

---

## Build and Run Commands

### Install

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# Edit .env with your SMTP credentials and local model paths
```

### Run the Interactive Pipeline

```bash
python -m src.main run
```

Prompts for city, business type, lead count, and channels (email / whatsapp). Then runs: discover → audit → research → generate pitch → ask for approval → send.

### Start the Dashboard

```bash
python -m src.main dashboard
```

Opens at `http://127.0.0.1:8080` (port configurable via `.env`).

### Summary Reports

```bash
python -m src.main summary --city Mumbai   # per-city
python -m src.main summary                  # all cities
```

### Reset Outreach for a City

```bash
python -m src.main reset --city Mumbai
```

Resets all outreach statuses to `pending` so you can retry.

### Run Tests

```bash
pytest
```

All tests use mocked external dependencies (Playwright, SMTP, VLM). No real browsers or APIs are invoked during testing.

---

## Code Style Guidelines

- **Docstrings**: Every module, class, and public function must have a docstring. Use Google-style or plain descriptive sentences.
- **Type hints**: Use full type annotations (`list[dict[str, Any]]`, `str | None`). Import `from __future__ import annotations` in newer modules to avoid string-forward-reference issues.
- **Imports**: Group as (1) stdlib, (2) third-party, (3) local `src.*` modules. Separate groups with a blank line.
- **Private helpers**: Prefix module-private functions with `_` (e.g., `_load_local_model`, `_build_prompts`).
- **Custom exceptions**: Each module defines its own exception class (e.g., `DiscoveryError`, `WhatsAppError`, `PageMapError`, `VisionEngineError`).
- **Strings**: Prefer double quotes.
- **Constants**: Module-level constants use UPPER_SNAKE_CASE (e.g., `CARD_SELECTORS`).
- **Logging**: Use `logging.getLogger(__name__)` in modules that perform I/O or automation. The CLI modules use `rich.console.Console` for user-facing output.
- **Settings access**: Always go through `src.config.get_settings()`. It returns a cached `Settings` instance loaded from `.env`.
- **Database sessions**: Prefer explicit `db.close()` in CLI code; use `src.database.get_db()` generator for FastAPI dependencies.
- **Datetime**: Always use UTC (`datetime.now(timezone.utc)`).

---

## Module Reference

### Core Data Layer

- **`src/models.py`** — `Lead` and `Outreach` SQLAlchemy models. Uses `Mapped` / `mapped_column` (SQLAlchemy 2.0 style). `Lead` has a unique constraint on `(city, business_name)`.
- **`src/database.py`** — `init_db()`, `get_engine()`, `get_sessionmaker()`, `get_db()`.
- **`src/tracker.py`** — `get_or_create_lead()`, `is_already_contacted()`, `log_outreach()`, `get_city_summary()`, `get_all_cities()`.

### Automation Layer

- **`src/discovery.py`** — `GoogleMapsScraper.discover(city, category, max_leads)` returns a list of lead dicts. Uses a **three-tier fallback** for resilience:
  1. Direct Playwright selectors (fastest)
  2. Accessibility-tree mapper (`vision_mapper.py`)
  3. Vision agent (`vision_agent.py`) as final fallback
- **`src/website_auditor.py`** — `WebsiteAuditor.audit(url)` returns a dict with `overall_score` (`good` | `needs_work` | `poor`), `layout_issues`, `old_tech_detected`, `load_time_ms`, etc. Runs desktop + mobile viewport checks.
- **`src/researcher.py`** — `LinkedInResearcher.research(lead)` scrapes Bing for LinkedIn company pages, then generates a pitch via the **local VLM** (`llama-cpp-python`). Falls back to a static contextual pitch if the model fails or is unavailable.
- **`src/messenger.py`** — `EmailSender` (smtplib) and `WhatsAppSender` (Playwright on WhatsApp Web). WhatsApp uses a persistent browser context saved to `whatsapp_session/`.

### Vision Subsystem

The vision subsystem is a **perceive-plan-act loop** using a local VLM:

- **`src/vision_engine.py`** — `capture_screenshot()`, `_get_interactive_elements()`, `annotate_screenshot()`, `build_vision_prompt()`, `parse_action()`, `_query_local_vlm()`.
- **`src/vision_executor.py`** — `VisionExecutor.execute(action)` maps `VisionAction` (click, fill, press, scroll, wait, done) to Playwright commands.
- **`src/vision_agent.py`** — `VisionAgent.run_task(task)` runs the loop: screenshot → detect elements → annotate → prompt VLM → parse JSON action → execute → repeat up to `max_steps`.
- **`src/vision_mapper.py`** — Text-only fallback. Builds an accessibility-tree `PageMap` via JavaScript DOM walker. Provides `safe_click()` and `safe_fill()` with vision-agent fallback.

### Presentation Layer

- **`src/summarizer.py`** — `Summarizer.city_summary()` / `all_cities_summary()` prints Rich tables to the terminal.
- **`src/dashboard.py`** — FastAPI app with routes: `/`, `/leads`, `/leads/{id}`, `/cities/{city}`, `/api/stats`, `/drafts`, `/drafts/{filename}`. Uses Jinja2 templates.

---

## Testing Instructions

- **Framework**: pytest.
- **Fixtures** (`tests/conftest.py`):
  - `temp_db` — creates a fresh SQLite DB per test.
  - `mock_playwright` — provides a mocked Playwright browser/context/page chain.
- **Mocking strategy**: All Playwright browser automation, SMTP, and VLM inference is mocked. Tests verify orchestration logic, error handling, and data transformations. No real network calls or browser windows are opened.
- **Run all tests**:
  ```bash
  pytest
  ```
- **Run a specific module**:
  ```bash
  pytest tests/test_discovery.py -v
  ```
- **Key test patterns**:
  - Patch `src.main.GoogleMapsScraper` to test pipeline logic without real scraping.
  - Patch `smtplib.SMTP` to test email sending.
  - Patch `httpx.post` or `_load_local_model` to test pitch generation.
  - Use `tmp_path` for filesystem-related tests (screenshots, drafts).

---

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com

# Local VLM (priority over Ollama)
LOCAL_MODEL_PATH=/home/pranavvv/models/qwen3.5-9b/qwen_3.5_9B_Q4_K_M.gguf

# VLM directory (contains .gguf + mmproj)
VLM_MODEL_DIR=/home/pranavvv/models/qwen3.5-VLM-9b
VLM_MODEL_FILE=Qwen3.5-9B-Q4_K_M.gguf
VLM_MMPROJ_FILE=mmproj-F16.gguf

# Vision toggles
USE_VISION=true
VISION_TIMEOUT_MS=30000
VISION_HEADED=true

# Database
DB_PATH=./data/leads.db

# WhatsApp
WHATSAPP_USER_DATA_DIR=./whatsapp_session

# Dashboard
DASHBOARD_PORT=8080
```

Settings are loaded via `pydantic-settings` in `src/config.py`. Extra keys in `.env` are ignored (`extra="ignore"`).

---

## Security Considerations

- **Credentials live in `.env`**. This file is gitignored. Never commit it.
- **SMTP password** should be an app-specific password, not the account password.
- **WhatsApp Web** runs in a headed or headless Chromium with persistent user data. The session directory (`whatsapp_session/`) contains authentication cookies — do not commit it.
- **Dashboard** binds to `127.0.0.1` only. It is not intended for public exposure.
- **Rate limiting**: WhatsApp messages have a hardcoded 3-second delay between sends. Google Maps uses exponential backoff with max 3 retries.
- **No input sanitization** is performed on scraped business data before DB storage. Treat DB contents as untrusted if exporting.

---

## Common Patterns

### Adding a New Business Type for Pitches

Edit `src/researcher.py` → `LinkedInResearcher._build_prompts()` → `type_contexts` dict. Add the lowercase category as key and a context string as value. The CLI already accepts `custom` categories.

### Adding a New Dashboard Route

Edit `src/dashboard.py`, add a `@app.get(...)` or `@app.post(...)` handler, then create the corresponding Jinja2 template in `src/templates/`. Extend `base.html` for consistent styling.

### Extending the Vision Agent

- New actions: add handling in `VisionExecutor.execute()` and update the rules in `vision_engine.build_vision_prompt()`.
- New element detection: modify `_get_interactive_elements()` in `vision_engine.py`.

### Database Migrations

This project does **not** use Alembic. Schema changes are applied by modifying `src/models.py` and deleting/recreating the SQLite file (`data/leads.db`), or by manually running `ALTER TABLE` statements. The `init_db()` function calls `Base.metadata.create_all()` which only creates missing tables.

---

## Troubleshooting Notes

- `Ollama connection refused` → The app now prefers the **local GGUF model** via `llama-cpp-python`. Ensure the file at `LOCAL_MODEL_PATH` exists. If the local model is missing, the researcher falls back to Ollama HTTP API.
- `WhatsApp QR keeps appearing` → Delete `whatsapp_session/` and rescan.
- `Google Maps empty results` → Check network, try fewer leads, or inspect `screenshots/` for visual diagnostics.
- `DiscoveryError` / `PageMapError` → The scraper saves screenshots and page-map text files to `screenshots/` on failure.
