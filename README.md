# Client Acquisition System

Automated discovery, research, and outreach to local businesses via Google Maps, LinkedIn, and AI-generated pitches sent through Email and WhatsApp. Includes a visual dashboard for tracking.

## Features

- **Google Maps Discovery** — Scrape local business listings by city and category
- **LinkedIn Research** — Enrich leads with company info and years in business
- **AI Pitch Generation** — Local Ollama (Qwen 3.5 9B) writes personalized website development pitches tailored to each business type (cafe, salon, retail, clinic, etc.)
- **Email & WhatsApp Outreach** — Send pitches via SMTP or WhatsApp Web
- **Deduplication** — Never contact the same business in the same city twice
- **Dashboard** — FastAPI web UI to browse leads, messages, and city reports

## Setup

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com/) running locally with your model (e.g., `qwen2.5:9b`)
- Google Chrome / Chromium (installed by Playwright)

### Installation

```bash
# Clone / enter project
cd acquire_clients

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### Environment Variables

```bash
# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com

# Ollama (local AI)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:9b

# Paths
DB_PATH=./data/leads.db
WHATSAPP_USER_DATA_DIR=./whatsapp_session

# Dashboard
DASHBOARD_PORT=8080
```

### Start Ollama

```bash
ollama serve
# In another terminal, ensure your model is pulled:
ollama pull qwen2.5:9b
```

## Usage

### Interactive Pipeline

```bash
python -m src.main run
```

This will:
1. Ask which city to target
2. Ask business type (all, cafe, salon, retail, clinic, etc.)
3. Ask how many leads
4. Check existing DB for duplicates and ask to skip
5. Open WhatsApp Web (if selected) for QR scan
6. Scrape Google Maps
7. Research each business on LinkedIn
8. Generate AI pitch
9. Show you the pitch and ask if you want to send
10. Send via Email / WhatsApp
11. Print summary

### Dashboard

```bash
python -m src.main dashboard
```

Open `http://127.0.0.1:8080` to view:
- Overall stats (total leads, sent, failed, responded)
- Per-city reports with pie charts
- Lead table with filters
- Lead detail pages with full outreach history

### Summary Reports

```bash
# City-specific
python -m src.main summary --city Mumbai

# All cities
python -m src.main summary
```

### Reset Outreach for a City

```bash
python -m src.main reset --city Mumbai
```

This resets all outreach statuses to "pending" so you can retry.

## Architecture

```
src/
  config.py       — Pydantic settings from .env
  models.py       — SQLAlchemy Lead & Outreach models
  database.py     — SQLite engine & session management
  tracker.py      — Deduplication, logging, city summaries
  discovery.py    — Playwright Google Maps scraper
  researcher.py   — LinkedIn lookup + Ollama AI pitch
  messenger.py    — SMTP email + WhatsApp Web sender
  summarizer.py   — Rich CLI tables and reports
  dashboard.py    — FastAPI + Jinja2 web UI
  main.py         — CLI entry point with argparse
```

## Smart Pitch Generation

The AI prompt adapts automatically based on business type:

| Type | Focus |
|------|-------|
| Cafe / Restaurant | Online menu, table booking, Instagram |
| Salon / Spa | Appointment booking, service catalog, gallery |
| Retail | Product showcase, e-commerce readiness |
| Clinic / Medical | Trust, credentials, appointment scheduling |
| Generic | Modern responsive site, inquiries, credibility |

If Ollama is unavailable, a contextual fallback pitch is used.

## WhatsApp Web

- WhatsApp opens in a **headed Chrome window** at startup
- Scan the QR code with your phone
- Session is saved to `whatsapp_session/` — no need to scan again
- If the session expires, the browser will show the QR again

## Rate Limits & Safety

- WhatsApp: 3-second delay between messages to avoid bans
- Google Maps: exponential backoff on retries (max 3)
- Email: standard SMTP rate limits apply (use app passwords)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Ollama connection refused` | Run `ollama serve` |
| WhatsApp QR keeps appearing | Delete `whatsapp_session/` and rescan |
| Google Maps empty results | Check network, try fewer leads, or manually verify Maps layout |
| SMTP auth failed | Use app-specific password (not your Gmail password) |
| Duplicate contacts | System auto-skips; run `reset` if you want to retry |

## License

MIT
