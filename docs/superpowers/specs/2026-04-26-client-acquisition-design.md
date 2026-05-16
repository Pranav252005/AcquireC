# Client Acquisition System — Design Document

**Date:** 2026-04-26  
**Approach:** CLI + Local Web Dashboard (Approach 3)  
**Goal:** Automate discovery, research, and outreach to local businesses via Google Maps, LinkedIn, AI-generated pitches, email, and WhatsApp — with a visual dashboard for tracking.

---

## 1. Overview

A CLI tool backed by a local FastAPI dashboard. The user runs the CLI, answers prompts (city, business type, number of leads), and the system:
1. Scrapes Google Maps for businesses in the target city
2. Checks the SQLite DB to avoid re-contacting previously-targeted businesses
3. Researches each business via LinkedIn (company page + key people)
4. Uses a local Ollama model (Qwen 3.5 9B) to generate a hyper-personalized website development pitch
5. Sends outreach via SMTP email and/or WhatsApp Web (headed Chrome, QR scan at startup)
6. Logs everything to SQLite with per-city deduplication
7. Serves a local dashboard to browse leads, messages, and statuses

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI (main.py)                       │
│  Prompts user → runs pipeline → prints summary              │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  ┌──────────┐        ┌──────────────┐       ┌──────────┐
  │ discovery│        │  researcher  │       │ messenger│
  │  (play-  │   ──▶ │ (playwright  │  ──▶ │(email/   │
  │ wright)  │        │  + ollama)   │       │ whatsapp)│
  └──────────┘        └──────────────┘       └──────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │ tracker (SQLite)│
                    │    leads.db     │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ dashboard (FastAPI│
                    │ + vanilla HTML)  │
                    └─────────────────┘
```

### Modules

| Module | Responsibility |
|--------|---------------|
| `config.py` | Load `.env`, expose settings (email, Ollama URL, DB path, etc.) |
| `models.py` | SQLAlchemy models: `Lead`, `Outreach`, `CityStats` |
| `database.py` | Engine, session factory, init schema |
| `discovery.py` | Playwright scraper for Google Maps business listings |
| `researcher.py` | Playwright LinkedIn lookup + Ollama AI pitch generation |
| `messenger.py` | SMTP email sender + WhatsApp Web (Playwright, headed) |
| `tracker.py` | DB CRUD: dedup by city+name, log outreach, update status |
| `summarizer.py` | CLI commands for per-city summary reports |
| `dashboard.py` | FastAPI app with HTML endpoints for visual browsing |
| `main.py` | CLI entry point: argparse commands + interactive prompts |

---

## 3. Data Model

### `Lead`
- `id` (PK)
- `city` (str, indexed)
- `business_name` (str, indexed)
- `business_type` (str, e.g., "cafe", "salon")
- `address` (str)
- `phone` (str, nullable)
- `email` (str, nullable)
- `website` (str, nullable)
- `google_maps_url` (str)
- `linkedin_url` (str, nullable)
- `linkedin_summary` (str, nullable) — scraped description
- `years_in_business` (int, nullable) — inferred from LinkedIn
- `menu_or_services` (str, nullable) — extracted offering text
- `created_at`
- `updated_at`
- UNIQUE constraint: (`city`, `business_name`)

### `Outreach`
- `id` (PK)
- `lead_id` (FK → Lead)
- `channel` (enum: "email" | "whatsapp")
- `message_text` (text)
- `context_summary` (text) — why this pitch was chosen
- `status` (enum: "pending" | "sent" | "failed" | "responded")
- `error_message` (text, nullable)
- `sent_at` (datetime, nullable)
- `created_at`

---

## 4. Component Designs

### 4.1 Discovery (`discovery.py`)
**Input:** city name, business category keyword (e.g., "cafe", "salon", "all"), max leads
**Output:** list of `Lead` objects (name, address, phone, website, maps URL)

**Behavior:**
- Launch headed Chrome via Playwright
- Navigate to Google Maps, search `{business_category} in {city}`
- Scroll through results, extract listing cards
- Parse: name, address, phone (if visible), website link, Maps URL
- Return list; caller filters against DB for dedup

**Edge cases:**
- Google Maps rate limits → exponential backoff, max 3 retries
- No phone/email → still store lead, mark as "no_contact_info"
- Captcha → pause, notify user in CLI, continue on manual solve

### 4.2 Researcher (`researcher.py`)
**Input:** `Lead` object
**Output:** enriched `Lead` + generated pitch string

**Behavior:**
- Search LinkedIn for company page matching business name + city
- If found: scrape company description, industry, employee count, year founded
- Search LinkedIn for founders/owners by name if possible
- Pass gathered context to Ollama (Qwen 3.5 9B) via local API
- **Prompt engineering:** dynamic prompt based on `business_type`:
  - Cafe: "They serve [menu_items]. Pitch a modern website with online menu, table booking, and Instagram integration."
  - Salon/Spa: "They offer [services]. Pitch a booking website with service catalog and reviews."
  - Retail: "They sell [products]. Pitch an e-commerce-ready showcase site."
  - Clinic/Professional: "They provide [services]. Pitch a professional site with appointment booking and credentials."
  - Generic: "They are a [type] business. Pitch a modern responsive website that builds trust and drives inquiries."
- AI returns: `pitch_text`, `key_selling_points`, `estimated_budget_hint` (optional)
- Store `linkedin_summary`, `years_in_business`, `menu_or_services` on Lead

### 4.3 Messenger (`messenger.py`)
**Input:** `Lead`, pitch text, channel (email/whatsapp/both)
**Output:** `Outreach` record with status

**Email:**
- Use `smtplib` with credentials from `.env`
- Subject: "Quick thought about {business_name}'s online presence"
- Body: personalized pitch + portfolio link + CTA
- Mark "sent" or "failed" with error

**WhatsApp:**
- Playwright opens `web.whatsapp.com` in a **persistent browser context** (user data dir)
- At **first run / if not authenticated**, show QR code in headed Chrome
- User scans QR → session saved to `whatsapp_session/` directory
- Subsequent runs reuse saved session (no QR needed)
- To send: navigate to `https://web.whatsapp.com/send?phone={phone}`, wait for chat, type message, send
- Handle "Phone number not on WhatsApp" → mark "failed", store error

### 4.4 Tracker (`tracker.py`)
**Input:** city, business name
**Output:** boolean (already contacted?)

**Behavior:**
- Query `Lead` + `Outreach` by city + name
- If lead exists AND has at least one "sent" outreach → skip
- If lead exists with only "pending" or all "failed" → allow retry, prompt user
- If lead exists with "responded" → skip, flag for follow-up list

**Summaries:**
- `get_city_summary(city)` → counts: total leads, contacted, pending, failed, responded
- `get_all_cities()` → list of cities with counts

### 4.5 Dashboard (`dashboard.py`)
**Framework:** FastAPI + Jinja2 + vanilla HTML/CSS (no React, minimal deps)

**Routes:**
- `GET /` → Dashboard homepage with stats cards (total leads, sent, failed, responded)
- `GET /leads` → Table of all leads, filterable by city and status
- `GET /leads/{lead_id}` → Lead detail page: info, outreach history, AI pitch text
- `GET /cities/{city}` → City report: pie chart of statuses, list of leads
- `GET /api/stats` → JSON endpoint for frontend charts

**Visual:**
- TailwindCSS CDN for styling (no build step)
- Simple pie chart via Chart.js CDN
- Search/filter bar on leads page

### 4.6 CLI (`main.py`)
**Commands:**
- `python -m src.main run` → Interactive mode:
  1. "Which city to focus on today?"
  2. "What business type? (all / cafe / salon / retail / clinic / custom)"
  3. "How many leads? (default 20)"
  4. Show existing city stats: "You already contacted 12/45 businesses in Mumbai. Skip them? [Y/n]"
  5. Run discovery → show progress bar
  6. Research each → show progress
  7. Show generated messages for review: "Send to {name}? [Y/n/skip/edit]"
  8. Send via chosen channels → log results
  9. Print summary: sent X, failed Y, skipped Z

- `python -m src.main summary --city Mumbai` → Text report
- `python -m src.main dashboard` → Start FastAPI server on `localhost:8080`
- `python -m src.main reset --city Mumbai` → Clear outreach records for city (keep leads)

---

## 5. Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Web Scraping | Playwright (sync API) |
| AI | Ollama local API (Qwen 3.5 9B) |
| DB | SQLite + SQLAlchemy 2.0 |
| Dashboard | FastAPI + Jinja2 + TailwindCSS CDN + Chart.js CDN |
| Email | `smtplib` (std lib) |
| Env Config | `python-dotenv` |
| CLI | `argparse` + `rich` (progress bars, tables) |
| Testing | `pytest` + `pytest-playwright` |

---

## 6. File Structure

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
│   ├── discovery.py
│   ├── researcher.py
│   ├── messenger.py
│   ├── tracker.py
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
│   ├── test_discovery.py
│   ├── test_researcher.py
│   ├── test_messenger.py
│   ├── test_tracker.py
│   └── test_dashboard.py
├── data/
│   └── leads.db
├── whatsapp_session/
│   └── (persistent browser context)
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-26-client-acquisition-design.md
```

---

## 7. Error Handling & Edge Cases

- **Ollama not running:** Prompt user to start `ollama serve`, fallback to generic template pitch
- **LinkedIn login wall:** Use public company pages where possible; if blocked, skip LinkedIn enrichment, still generate pitch from Maps data
- **No contact info:** Store lead, skip messaging, flag as "needs_manual_contact"
- **WhatsApp Web session expired:** Detect "Keep your phone connected" or QR reappearance → prompt user to re-scan
- **SMTP failure:** Log error, mark outreach "failed", continue with other leads
- **Google Maps layout change:** Discovery module logs HTML snapshot to `screenshots/` for debugging

---

## 8. Security & Privacy

- Email password stored only in `.env` (never committed)
- WhatsApp session stored locally in `whatsapp_session/` (gitignored)
- No business data sent to external APIs except Ollama (local) and LinkedIn/Google (scraped)
- Rate limiting: max 1 message per 3 seconds to avoid WhatsApp bans

---

## 9. Success Criteria

- [ ] User can run `python -m src.main run`, answer prompts, and the system finds + contacts businesses
- [ ] Dashboard shows accurate per-city stats and lead details
- [ ] No duplicate outreach to the same business in the same city
- [ ] AI pitch is contextually relevant (cafe gets menu focus, salon gets booking focus)
- [ ] WhatsApp QR scan works at startup, session persists across runs
- [ ] Email sends successfully via SMTP
- [ ] Summary command prints clear reports

---

## 10. Future Enhancements (out of scope for v1)

- Auto-follow-up sequences for "sent but no response" leads
- Integration with Calendly/Cal.com for booking links in pitches
- AI response parsing (if lead replies, detect interest level)
- Multi-city parallel scraping
- Chrome extension for one-click "add this business" from Maps
