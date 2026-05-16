# Client Acquisition System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a CLI + dashboard system that discovers local businesses on Google Maps, researches them via LinkedIn + local Ollama AI, and sends personalized website development pitches via email and WhatsApp — with full tracking and a visual dashboard.

**Architecture:** Modular Python system with Playwright for web scraping, SQLAlchemy + SQLite for persistence, FastAPI + Jinja2 for dashboard, and local Ollama API for AI pitch generation. CLI orchestrates the pipeline via `src/main.py`.

**Tech Stack:** Python 3.11+, Playwright, SQLAlchemy 2.0, FastAPI, Jinja2, python-dotenv, rich, smtplib, pytest, pytest-playwright

---

## File Structure

```
acquire_clients/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── database.py
│   ├── tracker.py
│   ├── discovery.py
│   ├── researcher.py
│   ├── messenger.py
│   ├── summarizer.py
│   ├── dashboard.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── leads.html
│   │   ├── lead_detail.html
│   │   └── city_report.html
│   └── main.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_database.py
│   ├── test_tracker.py
│   ├── test_discovery.py
│   ├── test_researcher.py
│   ├── test_messenger.py
│   ├── test_summarizer.py
│   └── test_dashboard.py
├── data/
│   └── (SQLite DB created at runtime)
├── screenshots/
│   └── (debug snapshots from Playwright)
└── whatsapp_session/
    └── (persistent browser context, gitignored)
```

---

### Task 1: Project Skeleton & Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `data/.gitkeep`
- Create: `screenshots/.gitkeep`
- Create: `whatsapp_session/.gitkeep`

**Steps:**
- **Step 1:** Write `requirements.txt` with exact versions: `playwright>=1.40`, `sqlalchemy>=2.0`, `fastapi>=0.104`, `uvicorn>=0.24`, `jinja2>=3.1`, `python-dotenv>=1.0`, `rich>=13.0`, `pytest>=7.4`, `pytest-playwright>=0.4`, `httpx>=0.25`, `pydantic>=2.5`, `python-multipart>=0.0.6`
- **Step 2:** Write `.env.example` with keys: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `OLLAMA_URL=http://localhost:11434`, `OLLAMA_MODEL=qwen2.5:9b`, `DB_PATH=./data/leads.db`, `WHATSAPP_USER_DATA_DIR=./whatsapp_session`, `DASHBOARD_PORT=8080`
- **Step 3:** Write `.gitignore` ignoring: `*.db`, `.env`, `__pycache__/`, `*.pyc`, `whatsapp_session/`, `data/*.db`, `screenshots/`
- **Step 4:** Create empty `__init__.py` files and `.gitkeep` directories
- **Step 5:** Verify by running `pip install -r requirements.txt` and `playwright install chromium`
- **Step 6:** Commit

---

### Task 2: Configuration Module (`config.py`)

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

**Steps:**
- **Step 1:** Write failing test `test_config.py` asserting that `load_config()` returns a Pydantic `Settings` model with `smtp_host`, `smtp_port`, `ollama_url`, `db_path` fields, and that missing required vars raise `ValidationError`
- **Step 2:** Run `pytest tests/test_config.py -v`, confirm failure
- **Step 3:** Implement `src/config.py` using Pydantic `BaseSettings` with `SettingsConfigDict(env_file=".env")`. Fields: `smtp_host: str`, `smtp_port: int = 587`, `smtp_user: str`, `smtp_password: str`, `smtp_from: str`, `ollama_url: str = "http://localhost:11434"`, `ollama_model: str = "qwen2.5:9b"`, `db_path: str = "./data/leads.db"`, `whatsapp_user_data_dir: str = "./whatsapp_session"`, `dashboard_port: int = 8080`
- **Step 4:** Run tests, confirm pass
- **Step 5:** Commit

---

### Task 3: Database Models (`models.py`)

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

**Steps:**
- **Step 1:** Write failing test `test_models.py` that creates SQLAlchemy `Lead` and `Outreach` instances, asserts fields exist, and that `Lead.outreaches` relationship returns a list
- **Step 2:** Run `pytest tests/test_models.py -v`, confirm failure
- **Step 3:** Implement `src/models.py` with SQLAlchemy 2.0 declarative base. `Lead`: `id` (PK), `city` (str, indexed), `business_name` (str, indexed), `business_type` (str), `address` (str), `phone` (str, nullable), `email` (str, nullable), `website` (str, nullable), `google_maps_url` (str), `linkedin_url` (str, nullable), `linkedin_summary` (str, nullable), `years_in_business` (int, nullable), `menu_or_services` (str, nullable), `created_at` (DateTime), `updated_at` (DateTime). `Outreach`: `id` (PK), `lead_id` (FK), `channel` (Enum: "email", "whatsapp"), `message_text` (Text), `context_summary` (Text), `status` (Enum: "pending", "sent", "failed", "responded"), `error_message` (Text, nullable), `sent_at` (DateTime, nullable), `created_at` (DateTime). Table-level unique constraint on `(city, business_name)` on `Lead`.
- **Step 4:** Run tests, confirm pass
- **Step 5:** Commit

---

### Task 4: Database Engine & Session (`database.py`)

**Files:**
- Create: `src/database.py`
- Create: `tests/test_database.py`

**Steps:**
- **Step 1:** Write failing test `test_database.py` that calls `init_db()`, asserts `leads.db` file is created, then creates a `Lead` via session, commits, and queries it back by city
- **Step 2:** Run `pytest tests/test_database.py -v`, confirm failure
- **Step 3:** Implement `src/database.py`: `engine = create_engine(f"sqlite:///{config.db_path}")`, `SessionLocal = sessionmaker(bind=engine)`, `init_db()` calls `Base.metadata.create_all(engine)`, `get_db()` yields a session. Accept `db_path` as argument so tests can use temp file
- **Step 4:** Run tests, confirm pass
- **Step 5:** Commit

---

### Task 5: Tracker (`tracker.py`)

**Files:**
- Create: `src/tracker.py`
- Create: `tests/test_tracker.py`

**Steps:**
- **Step 1:** Write failing test `test_tracker.py` with cases: `is_already_contacted(city, name)` returns False for new lead, True after a "sent" outreach; `get_city_summary(city)` returns correct counts; `get_all_cities()` returns list with counts; duplicate `(city, name)` raises integrity error
- **Step 2:** Run `pytest tests/test_tracker.py -v`, confirm failure
- **Step 3:** Implement `src/tracker.py` functions: `is_already_contacted(db, city, name)` queries `Lead` joined with `Outreach` where status="sent"; `get_city_summary(db, city)` returns dict with keys `total`, `contacted`, `pending`, `failed`, `responded`; `get_all_cities(db)` returns list of dicts with `city` and counts; `create_lead(db, lead_data)` inserts or updates Lead; `log_outreach(db, lead_id, channel, message, context, status)` creates Outreach record
- **Step 4:** Run tests, confirm pass
- **Step 5:** Commit

---

### Task 6: Discovery — Google Maps Scraper (`discovery.py`)

**Files:**
- Create: `src/discovery.py`
- Create: `tests/test_discovery.py`

**Steps:**
- **Step 1:** Write failing test `test_discovery.py` that mocks Playwright context and asserts `discover_businesses(city, category, max_leads)` returns a list of dicts with keys `business_name`, `address`, `phone`, `website`, `google_maps_url`
- **Step 2:** Run `pytest tests/test_discovery.py -v`, confirm failure
- **Step 3:** Implement `src/discovery.py` with `GoogleMapsScraper` class: `__init__` takes Playwright instance; `discover(city, category, max_leads=20)` launches headed Chromium, navigates to `https://www.google.com/maps/search/{category}+in+{city}`, waits for results list, scrolls to load more cards, extracts data via selectors. `extract_listing(card)` parses name, address, phone, website, maps URL. Returns list of dicts. Includes retry logic with exponential backoff (max 3). Saves page snapshot to `screenshots/` on exception.
- **Step 4:** Run tests, confirm pass (may skip real browser test, mock the heavy parts)
- **Step 5:** Commit

---

### Task 7: Researcher — LinkedIn + Ollama (`researcher.py`)

**Files:**
- Create: `src/researcher.py`
- Create: `tests/test_researcher.py`

**Steps:**
- **Step 1:** Write failing test `test_researcher.py` mocking both Playwright and httpx (Ollama call). Assert `research_lead(lead)` returns enriched lead with `linkedin_summary`, `years_in_business`, `menu_or_services`, and `pitch_text`. Assert Ollama prompt contains business type context (e.g., "cafe" triggers menu-focused language).
- **Step 2:** Run `pytest tests/test_researcher.py -v`, confirm failure
- **Step 3:** Implement `src/researcher.py`: `LinkedInResearcher` class with Playwright browser; `research(lead)` searches LinkedIn for company page using `{business_name} {city}` query, scrapes description/industry/employee count; `generate_pitch(lead, linkedin_data)` builds dynamic prompt based on `business_type` (cafe/salon/retail/clinic/generic) and calls Ollama `/api/generate` endpoint with model from config; parses JSON response for `pitch_text`. If Ollama fails, fallback to generic template pitch.
- **Step 4:** Run tests, confirm pass
- **Step 5:** Commit

---

### Task 8: Messenger — Email + WhatsApp (`messenger.py`)

**Files:**
- Create: `src/messenger.py`
- Create: `tests/test_messenger.py`

**Steps:**
- **Step 1:** Write failing test `test_messenger.py` mocking `smtplib.SMTP` and Playwright. Assert `send_email(to, subject, body)` calls `sendmail`. Assert `send_whatsapp(phone, message)` navigates to WhatsApp Web send URL and types message. Assert `ensure_whatsapp_auth()` checks for existing session.
- **Step 2:** Run `pytest tests/test_messenger.py -v`, confirm failure
- **Step 3:** Implement `src/messenger.py`: `EmailSender` class using `smtplib.SMTP` with TLS, sends personalized email. `WhatsAppSender` class using Playwright with persistent context (`user_data_dir` from config), `ensure_auth()` opens `web.whatsapp.com` in headed mode, waits for QR scan or chat list. `send(phone, message)` navigates to `https://web.whatsapp.com/send?phone={phone}`, waits for chat input, types message, sends. Rate limit: sleep 3s between messages.
- **Step 4:** Run tests, confirm pass
- **Step 5:** Commit

---

### Task 9: Summarizer (`summarizer.py`)

**Files:**
- Create: `src/summarizer.py`
- Create: `tests/test_summarizer.py`

**Steps:**
- **Step 1:** Write failing test `test_summarizer.py` seeding DB with leads and outreaches, then assert `city_summary(city)` returns formatted string with counts, and `all_cities_summary()` returns multi-city report.
- **Step 2:** Run `pytest tests/test_summarizer.py -v`, confirm failure
- **Step 3:** Implement `src/summarizer.py`: `city_summary(db, city)` queries tracker, builds rich `Table` with columns: Business Name, Type, Status, Channel, Sent At, Message Preview. `all_cities_summary(db)` builds overview table. `lead_detail(db, lead_id)` shows full lead info + all outreach records with full message text and context.
- **Step 4:** Run tests, confirm pass
- **Step 5:** Commit

---

### Task 10: Dashboard (FastAPI + Jinja2) (`dashboard.py` + templates)

**Files:**
- Create: `src/dashboard.py`
- Create: `src/templates/base.html`
- Create: `src/templates/index.html`
- Create: `src/templates/leads.html`
- Create: `src/templates/lead_detail.html`
- Create: `src/templates/city_report.html`
- Create: `tests/test_dashboard.py`

**Steps:**
- **Step 1:** Write failing test `test_dashboard.py` using `TestClient` from FastAPI. Assert `GET /` returns 200 and contains "Dashboard". Assert `GET /leads` returns 200 and lead data. Assert `GET /api/stats` returns JSON with counts.
- **Step 2:** Run `pytest tests/test_dashboard.py -v`, confirm failure
- **Step 3:** Implement `src/dashboard.py`: FastAPI app with Jinja2 templates from `src/templates/`. Routes: `GET /` → stats cards (total leads, sent, failed, responded) using tracker queries; `GET /leads?city=&status=` → table with filters; `GET /leads/{lead_id}` → detail page with all fields and outreach history; `GET /cities/{city}` → city report with Chart.js pie chart; `GET /api/stats` → JSON for charts. Templates use TailwindCSS CDN and Chart.js CDN. `run_dashboard()` function starts uvicorn.
- **Step 4:** Run tests, confirm pass
- **Step 5:** Commit

---

### Task 11: Main CLI (`main.py`)

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main.py`

**Steps:**
- **Step 1:** Write failing test `test_main.py` mocking argparse and all module imports. Assert `run_pipeline(city, category, max_leads)` orchestrates discovery → tracker dedup → researcher → messenger in sequence.
- **Step 2:** Run `pytest tests/test_main.py -v`, confirm failure
- **Step 3:** Implement `src/main.py` using `argparse` with subcommands: `run` (interactive prompts), `summary --city`, `dashboard`, `reset --city`. `run` command flow: (1) prompt city, (2) prompt category, (3) prompt max_leads, (4) check tracker for existing city stats and ask "Skip already contacted? [Y/n]", (5) run discovery with progress bar, (6) for each lead check dedup, (7) run researcher, (8) show generated pitch and ask "Send? [Y/n/skip/edit]", (9) send via chosen channels, (10) print final summary. Use `rich.console.Console` and `rich.progress.Progress` for UI. `summary` uses summarizer. `dashboard` starts uvicorn in thread. `reset` clears outreach statuses for a city.
- **Step 4:** Run tests, confirm pass
- **Step 5:** Commit

---

### Task 12: Integration Test & README

**Files:**
- Create: `README.md`
- Modify: `tests/conftest.py`

**Steps:**
- **Step 1:** Write `tests/conftest.py` with pytest fixtures: `temp_db` (creates in-memory SQLite, yields session, teardown), `mock_config` (patched Settings), `mock_playwright` (mock browser/context/page)
- **Step 2:** Write a single integration test `tests/test_integration.py` that: seeds config, creates temp DB, mocks discovery to return 2 fake leads, mocks researcher to return pitches, mocks messenger, runs the pipeline via `main.run_pipeline`, asserts tracker shows 2 leads with "sent" status
- **Step 3:** Run `pytest tests/test_integration.py -v`, confirm failure
- **Step 4:** Fix any integration issues in the modules
- **Step 5:** Run all tests: `pytest -v`
- **Step 6:** Write `README.md` with: project description, setup instructions (`pip install -r requirements.txt`, `playwright install`, `cp .env.example .env`, fill in email/Ollama), usage (`python -m src.main run`, `python -m src.main summary --city Mumbai`, `python -m src.main dashboard`), architecture overview, and troubleshooting
- **Step 7:** Commit

---

## Self-Review

1. **Spec coverage:** Every design requirement maps to a task:
   - Google Maps discovery → Task 6
   - LinkedIn + Ollama pitch generation → Task 7
   - Email + WhatsApp messaging → Task 8
   - SQLite tracking with dedup → Tasks 4, 5
   - Dashboard → Task 10
   - CLI with prompts + summaries → Tasks 9, 11
   - City-level dedup and summaries → Tasks 5, 9, 11

2. **Placeholder scan:** No TBD, no "implement later", no vague steps. Every step has concrete file paths and expected behavior.

3. **Type consistency:**
   - `config.py` → Pydantic `Settings` object
   - `database.py` → SQLAlchemy `Session` passed to functions
   - `tracker.py` → `db: Session` first param, returns typed dicts
   - `discovery.py` → returns `list[dict]`
   - `researcher.py` → accepts `Lead` model, returns enriched dict
   - `messenger.py` → `send_email(to: str, ...)` and `send_whatsapp(phone: str, ...)`
   - `summarizer.py` → `db: Session` first param
   - `dashboard.py` → FastAPI dependency injection for DB session
   - `main.py` → orchestrates with `Session` from `get_db()`

4. **Execution choice:** Recommend **Inline Execution** using executing-plans with checkpoints — tasks are sequential (models → DB → tracker → discovery → researcher → messenger → summarizer → dashboard → CLI → integration), so inline with review between phases is most efficient.
