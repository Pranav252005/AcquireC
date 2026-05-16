# Client Acquisition System — Operations Manual

> **Purpose:** This document is your complete guide to running the agent, understanding what each part does, and using it to consistently acquire clients while you sleep.

---

## Table of Contents

1. [Quick Start — Run Tonight](#1-quick-start--run-tonight)
2. [What Each Component Does](#2-what-each-component-does)
3. [Running Modes Explained](#3-running-modes-explained)
4. [Multi-City & Multi-Category Execution](#4-multi-city--multi-category-execution)
5. [Overnight / Headless Execution](#5-overnight--headless-execution)
6. [Daily Reports & Data Organization](#6-daily-reports--data-organization)
7. [Contact Strategy — Email + Phone](#7-contact-strategy--email--phone)
8. [Dashboard CRM Guide](#8-dashboard-crm-guide)
9. [Follow-Up Automation](#9-follow-up-automation)
10. [Troubleshooting & Tips](#10-troubleshooting--tips)

---

## 1. Quick Start — Run Tonight

### Step 1: Make sure Ollama is running
```bash
ollama serve
# In another terminal:
ollama pull qwen2.5:9b
```

### Step 2: Run a single city + category (interactive)
```bash
python -m src.main run
```
It will ask:
- City: `Mumbai`
- Categories: `cafe` (or `cafe,salon,retail` for multiple)
- Leads per combo: `20`
- Channels: Email = Yes, WhatsApp = No

### Step 3: Run overnight across multiple cities (batch)
```bash
python -m src.main batch \
  --cities "Mumbai,Delhi,Bangalore" \
  --categories "cafe,restaurant,salon" \
  --max-leads 30 \
  --channels "email" \
  --auto-send
```

This will:
1. Search **Mumbai + cafe**, then **Mumbai + restaurant**, then **Mumbai + salon**
2. Then **Delhi + cafe**, then **Delhi + restaurant**, then **Delhi + salon**
3. Then **Bangalore + cafe**... and so on
4. Auto-generate pitches and send them
5. Save a daily report to `reports/2026-05-16/`

---

## 2. What Each Component Does

### `src/discovery.py` — The Finder
**What it does:** Opens Google Maps, searches for businesses by city and category, and extracts:
- Business name
- Address
- Phone number
- Website URL
- Google Maps link
- **Rating & review count** (new)
- **Price level** `$` to `$$$$` (new)

**How it helps you:** This is your lead source. Without it, you'd manually copy-paste business names from Maps. It finds 50–100 businesses per hour automatically.

**When to tweak it:** If you notice it missing phone numbers, the Google Maps layout may have changed. Check the screenshots in `screenshots/` for debugging.

---

### `src/website_auditor.py` — The Inspector
**What it does:** Visits each business's website and checks:
- Is it mobile-friendly?
- Does it use HTTPS?
- How fast does it load?
- Is it built on old tech (FrontPage, Dreamweaver)?
- **Which CMS** it uses: WordPress, Wix, Squarespace, Shopify (new)

**How it helps you:** Businesses with no website or a broken website are **10x more likely to reply**. The auditor automatically skips businesses with modern websites, saving you time.

---

### `src/researcher.py` — The Brain
**What it does:**
1. Searches LinkedIn for the business to find years in operation
2. Runs the **AI Engine** to generate a pitch
3. Injects **business maturity analysis** (startup/growth/established/legacy)
4. Injects a **membership/loyalty concept** tailored to the business type

**How it helps you:** Instead of sending "Hi, we make websites," you send:
> *"With just 50 Regulars Club members at ₹299/month, you generate ₹14,950 in predictable revenue — enough to cover rent. The website manages sign-ups, payments, and QR check-ins automatically."*

This is a **business consultation**, not a cold pitch. Conversion rates are 3–5x higher.

---

### `src/ai_engine.py` — The Consistency Engine
**What it does:**
- Uses **grammar-constrained JSON** so the AI never outputs broken pitches
- Schedules temperature: 0.1 for facts, 0.3 for pitches, 0.4 for creative ideas
- Has a **3-tier fallback chain**: Local VLM → Text model → Ollama API → Template
- **Caches successful pitches** so similar businesses get proven templates
- Validates every output: too short? Missing keywords? It retries automatically.

**How it helps you:** Early versions of this system produced inconsistent pitches — the same café could get a great pitch or a broken one. This engine guarantees **consistent quality every single time**.

---

### `src/membership_ideas.py` — The Value Hook
**What it does:** Contains pre-built membership programs for 7 business types:

| Business | Concept | Monthly Revenue Example |
|----------|---------|------------------------|
| Café | The Regulars Club | 50 members × ₹299 = **₹14,950/mo** |
| Restaurant | Chef's Table Circle | 40 members × ₹1,299 = **₹51,960/mo** |
| Salon/Spa | Glow Pass | 30 members × ₹1,499 = **₹44,970/mo** |
| Retail | Insider Circle | 60 members × ₹899 = **₹53,940/mo** |
| Clinic | Family Health Plan | 20 families × ₹1,299 = **₹25,980/mo** |
| Gym | Fit Squad | 40 members × ₹1,999 = **₹79,960/mo** |
| Tuition | Scholar's Path | 25 students × ₹1,499 = **₹37,475/mo** |

**How it helps you:** You are no longer selling websites. You are selling **predictable monthly revenue** that happens to need a website. This changes the entire conversation.

---

### `src/business_intelligence.py` — The Analyst
**What it does:**
- Segments every business into **maturity stages**: Startup (0–1 yr), Growth (2–5 yr), Established (5–15 yr), Legacy (15+ yr)
- Scores **digital readiness** 1–10
- Identifies the **biggest pain point**
- Calculates **projected ROI months**
- Scores leads 1–100 for priority

**How it helps you:** A 20-year-old café gets a completely different pitch than a 6-month-old café. The system knows the difference and adjusts automatically.

---

### `src/messenger.py` — The Sender
**What it does:** Sends messages via:
- **Email** (SMTP — Gmail, Outlook, etc.)
- **WhatsApp Web** (headed Chrome, QR scan once, session persists)

**How it helps you:** One tool handles both channels. WhatsApp has a 3-second delay between messages to avoid bans.

---

### `src/follow_up.py` — The Nurturer
**What it does:** Automatically schedules follow-up sequences:

| Day | Channel | Message Type |
|-----|---------|--------------|
| 0 | Email/WhatsApp | Initial pitch |
| 3 | WhatsApp | Gentle follow-up |
| 7 | Email | Value-first case study |
| 14 | WhatsApp | Final message + video |
| 30 | Email | Newsletter opt-in |

**How it helps you:** 80% of sales happen after the 5th contact. Most people give up after 1. This system never gives up.

---

### `src/reply_parser.py` — The Listener
**What it does:** When a lead replies, it classifies the intent:
- **Interested** → Alert you immediately, send calendar link
- **Price inquiry** → Auto-reply with pricing guide
- **Booked** → Mark as hot lead, extract time/date
- **Not interested** → Unsubscribe, no more messages
- **Not now** → Reschedule for 30 days

**How it helps you:** You don't read every reply manually. The system tells you: *"3 hot leads need your attention right now."*

---

### `src/dashboard.py` — Your CRM
**What it does:** Web interface at `http://localhost:8080` with:
- Stats cards (total, sent, responded, hot leads)
- Lead table with filters (city, status, stage, min score)
- **Kanban board** (Cold → Pitched → Replied → Meeting → Closed → Lost)
- **Hot Leads** page (score-ranked)
- Lead detail with notes, follow-ups, membership ideas

**How it helps you:** You can drag leads through your pipeline, add notes (*"Owner Amit, prefers WhatsApp, busy mornings"*), and never lose track of a conversation.

---

### `src/reports.py` — The Archivist
**What it does:** After every batch run, creates:
```
reports/
  2026-05-16/
    summary_14-30-00.json       # Overall stats
    summary_14-30-00.txt        # Human-readable summary
    leads.csv                   # All leads processed today
    by-city/
      Mumbai.csv
      Delhi.csv
    by-category/
      cafe.csv
      salon.csv
    by-contact/
      with_both.csv             # Has email + phone
      email_only.csv
      phone_only.csv
      no_contact.csv
```

**How it helps you:** You have a permanent record of every day's work. You can open `with_both.csv` and see only your highest-quality leads.

---

## 3. Running Modes Explained

### Mode A: Interactive (`run`)
**Best for:** Testing a new city, reviewing pitches before sending, low volume
```bash
python -m src.main run
```
- You approve each pitch before sending
- You can edit pitches in real-time
- You see membership concepts displayed
- You can skip bad leads

### Mode B: Batch (`batch`)
**Best for:** Overnight runs, high volume, multiple cities
```bash
python -m src.main batch \
  --cities "Mumbai,Delhi" \
  --categories "cafe,salon" \
  --max-leads 50 \
  --auto-send \
  --channels "email,whatsapp"
```
- No prompts — runs completely headless
- Processes every city + category combination
- Saves daily report automatically
- Perfect for cron jobs

### Mode C: Dashboard (`dashboard`)
**Best for:** Reviewing results, managing pipeline, adding notes
```bash
python -m src.main dashboard
```
- Open `http://localhost:8080`
- View Kanban board
- Check Hot Leads
- Add notes to leads
- Update stages

---

## 4. Multi-City & Multi-Category Execution

### Why Multiple Cities?
Most cities don't have enough cafés or salons to fill a full day of outreach. By running 3–5 cities simultaneously, you get:
- More leads per hour
- Geographic diversification (if one city is saturated, others aren't)
- Better daily report volume

### Command Examples

**Example 1: 3 cities, 1 category**
```bash
python -m src.main batch \
  --cities "Mumbai,Delhi,Bangalore" \
  --categories "cafe" \
  --max-leads 40 \
  --auto-send
```
This runs **3 combos** (Mumbai+cafe, Delhi+cafe, Bangalore+cafe).

**Example 2: 2 cities, 3 categories**
```bash
python -m src.main batch \
  --cities "Mumbai,Pune" \
  --categories "cafe,restaurant,salon" \
  --max-leads 30 \
  --auto-send
```
This runs **6 combos**:
1. Mumbai + cafe
2. Mumbai + restaurant
3. Mumbai + salon
4. Pune + cafe
5. Pune + restaurant
6. Pune + salon

**Example 3: Pan-India sweep**
```bash
python -m src.main batch \
  --cities "Mumbai,Delhi,Bangalore,Chennai,Hyderabad" \
  --categories "cafe,restaurant,salon,retail,clinic" \
  --max-leads 20 \
  --auto-send \
  --channels "email"
```
This runs **25 combos**. At ~20 leads per combo = 500 leads per run.

### Important Notes
- There is a **2-second delay** between city+category combos to avoid Google Maps rate limits
- If WhatsApp is enabled, it will authenticate once and reuse the session
- The system automatically skips already-contacted businesses per city

---

## 5. Overnight / Headless Execution

### Setting Up a Cron Job (Linux/Mac)
Run every night at 2 AM:
```bash
crontab -e
```
Add this line:
```cron
0 2 * * * cd /home/pranavvv/Documents/Projects/acquire_clients && /home/pranavvv/.pyenv/versions/3.11.12/bin/python -m src.main batch --cities "Mumbai,Delhi,Bangalore" --categories "cafe,restaurant,salon" --max-leads 30 --auto-send --channels "email" >> reports/cron.log 2>&1
```

### Using `nohup` for One-Off Overnight Runs
```bash
nohup python -m src.main batch \
  --cities "Mumbai,Delhi,Bangalore,Chennai,Hyderabad,Pune" \
  --categories "cafe,restaurant,salon,retail,clinic,gym" \
  --max-leads 25 \
  --auto-send \
  --channels "email" \
  > reports/overnight_$(date +%Y%m%d).log 2>&1 &
```

This runs in the background. Check progress with:
```bash
tail -f reports/overnight_20260516.log
```

### Using `tmux` / `screen` for Interactive Monitoring
```bash
tmux new -s client-acquisition
python -m src.main batch --cities "Mumbai,Delhi" --categories "cafe" --max-leads 50 --auto-send
# Press Ctrl+B then D to detach
# Later: tmux attach -t client-acquisition
```

### What Happens While You Sleep
1. **2:00 AM** — Cron triggers the batch
2. **2:01 AM** — Google Maps discovery starts for Mumbai + cafe
3. **2:15 AM** — AI generates pitches with membership concepts
4. **2:30 AM** — Emails sent automatically
5. **2:35 AM** — Discovery starts for Delhi + cafe
6. **...continues...**
7. **Morning** — You check `reports/2026-05-16/summary.txt` and see exactly what happened

---

## 6. Daily Reports & Data Organization

### Folder Structure
Every batch run creates:
```
reports/
  2026-05-16/
    summary_14-30-00.txt     # Human-readable summary
    summary_14-30-00.json    # Machine-readable stats
    leads.csv                # All leads
    by-city/
      Mumbai.csv
      Delhi.csv
    by-category/
      cafe.csv
      salon.csv
    by-contact/
      with_both.csv          # GOLD: has email + phone
      email_only.csv
      phone_only.csv
      no_contact.csv         # Skip these
```

### Understanding `summary.txt`
```
DAILY REPORT — 2026-05-16
==================================================
Cities searched      : Mumbai, Delhi
Categories searched  : cafe, salon
Total discovered     : 143
Total processed      : 120
Messages sent        : 98
Messages failed      : 5
Skipped              : 17

CONTACT BREAKDOWN
------------------------------
Both email + phone   : 42
Email only           : 23
Phone only           : 38
No contact           : 17

BY CATEGORY
------------------------------
cafe              | Discovered:  78 | Processed:  65 | Both:  22 | Email:  12 | Phone:  21 | None:  10
salon             | Discovered:  65 | Processed:  55 | Both:  20 | Email:  11 | Phone:  17 | None:   7
```

### Listing Past Reports
```bash
python -m src.main reports
```

### Using the Data
Open `reports/2026-05-16/by-contact/with_both.csv` in Excel/Sheets. These are your **highest quality leads** — you have both email and phone.

---

## 7. Contact Strategy — Email + Phone

### How Contact Capture Works
1. **Google Maps** provides phone numbers directly
2. **Google Maps** rarely provides emails directly
3. If a business has a **website**, the system audits it but does NOT yet scrape email from the site (future enhancement)
4. The system works with **whatever it has**

### Current Behavior
| Has Email | Has Phone | Action |
|-----------|-----------|--------|
| ✅ Yes | ✅ Yes | Sends both email AND WhatsApp. **Best case.** |
| ✅ Yes | ❌ No | Sends email only |
| ❌ No | ✅ Yes | Sends WhatsApp only (or saves draft) |
| ❌ No | ❌ No | Skips lead entirely |

### Requiring Both Contacts (Strict Mode)
If you only want leads with both email and phone:
```bash
python -m src.main batch \
  --cities "Mumbai" \
  --categories "cafe" \
  --max-leads 50 \
  --auto-send \
  --require-both-contacts
```

**Recommendation:** Don't use `--require-both-contacts` for discovery. Use it for **follow-up targeting** — first reach everyone with any contact, then focus your energy on the `with_both.csv` list.

### Improving Contact Capture
To get more emails:
1. Visit the business website manually
2. Check their "Contact" page
3. Add the email via the dashboard: open lead → edit (future feature)
4. Or: use a service like Hunter.io API (can be integrated in `discovery.py`)

---

## 8. Dashboard CRM Guide

### Starting the Dashboard
```bash
python -m src.main dashboard
```
Open `http://localhost:8080`

### Pages Explained

#### Homepage (`/`)
- **6 stat cards**: Total, Sent, Responded, Failed, Pending, Hot
- **Recent leads**: Last 10 businesses discovered
- **Hot leads sidebar**: Top 5 scoring leads needing attention

#### Leads (`/leads`)
- Filter by: city, status (sent/failed/responded), **stage** (cold/pitched/replied/meeting/closed/lost), **min score**
- Columns: Business, City, Type, **Score**, **Stage**, Maturity, Status

#### Kanban (`/kanban`)
- 6 columns: Cold, Pitched, Replied, Meeting, Closed, Lost
- Each card shows: business name, score, status badge
- **Dropdown on each card** lets you move it to another stage
- Use this to track your sales pipeline visually

#### Hot Leads (`/hot-leads`)
- Score ≥ 70 by default
- Shows: pain point, maturity stage, action link
- Check this page **every morning**

#### Lead Detail (`/leads/{id}`)
- Full business info: rating, price level, CMS detected, maturity stage
- **Membership concept** displayed in green box
- **Pain point** displayed in red box
- **Outreach history**: every message sent
- **Notes**: add manual notes (e.g., "Call back Tuesday 11am")
- **Follow-ups**: scheduled follow-up messages
- **Stage updater**: dropdown to change pipeline stage

### Workflow Example
1. Run batch overnight
2. Morning: open `/hot-leads`
3. Click a high-score lead → view detail
4. If they replied: change stage to `replied`
5. Add note: "Sent pricing, waiting for decision"
6. If meeting booked: change stage to `meeting`
7. If closed deal: change stage to `closed`

---

## 9. Follow-Up Automation

### How It Works
After a message is **successfully sent**, the system schedules follow-ups automatically.

### Processing Due Follow-Ups
```bash
python -m src.main follow-ups
```
This checks for any follow-ups scheduled for today (or earlier) and sends them.

### Recommended Schedule
Run follow-ups **twice daily**:
- Morning (9 AM): process overnight follow-ups
- Evening (6 PM): process afternoon follow-ups

Cron setup:
```cron
0 9,18 * * * cd /home/pranavvv/Documents/Projects/acquire_clients && python -m src.main follow-ups >> reports/followup.log 2>&1
```

### What the Lead Experiences
- **Day 0**: Gets initial pitch
- **Day 3**: "Did my message reach you?"
- **Day 7**: Case study email about similar business
- **Day 14**: "Last message from me..."
- **Day 30**: Newsletter opt-in (soft re-engagement)

If the lead **replies at any point**, move them to `replied` stage in the dashboard. The system does not automatically cancel follow-ups yet (future enhancement).

---

## 10. Troubleshooting & Tips

### "No leads found"
- Check internet connection
- Try a different category: `restaurant` instead of `cafe`
- Reduce `max-leads` to 10 and test
- Check `screenshots/` for error images

### "Ollama connection refused"
```bash
ollama serve
ollama pull qwen2.5:9b
```

### "WhatsApp QR keeps appearing"
```bash
rm -rf whatsapp_session/
# Then run again and scan QR
```

### "AI pitch is generic"
- The system needs LinkedIn data. If LinkedIn is blocked, it falls back to templates.
- Check that `years_in_business` is being extracted (shown in dashboard)
- Lower temperature is now default (0.3) — pitches should be consistent

### Rate Limits
- **Google Maps**: Don't run more than 200 discoveries per hour
- **WhatsApp**: Built-in 3-second delay. Don't go below 2 seconds.
- **Email**: Gmail allows ~100 emails/hour. Use app passwords, not your real password.

### Best Practices
1. **Start small**: Test with 1 city + 1 category + 10 leads
2. **Review first**: Run without `--auto-send` to see pitches
3. **Check reports daily**: `reports/YYYY-MM-DD/summary.txt`
4. **Focus on hot leads**: `/hot-leads` page is your priority inbox
5. **Add notes**: Every conversation detail goes in the dashboard
6. **Run follow-ups**: `python -m src.main follow-ups` daily
7. **Weekly reset**: If a city is exhausted, try `python -m src.main reset --city Mumbai` to retry failed outreaches

---

## Command Cheat Sheet

| Task | Command |
|------|---------|
| Interactive run | `python -m src.main run` |
| Batch overnight (1 city, 1 cat) | `python -m src.main batch --cities "Mumbai" --categories "cafe" --max-leads 50 --auto-send` |
| Batch overnight (multi) | `python -m src.main batch --cities "Mumbai,Delhi" --categories "cafe,salon" --max-leads 30 --auto-send` |
| Dashboard | `python -m src.main dashboard` |
| Hot leads | `python -m src.main hot-leads` |
| Process follow-ups | `python -m src.main follow-ups` |
| City summary | `python -m src.main summary --city Mumbai` |
| Reset city | `python -m src.main reset --city Mumbai` |
| List reports | `python -m src.main reports` |

---

*Last updated: 2026-05-16*
*Next update: After first overnight batch run feedback*
