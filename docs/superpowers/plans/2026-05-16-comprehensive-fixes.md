# Comprehensive Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all 15 critical/serious/medium issues plus minor polish items without breaking existing functionality or tests.
**Architecture:** Refactor browser lifecycle into a shared pool, remove VLM from hot paths, replace LinkedIn with website-based enrichment, add proxy/logging/infrastructure, and improve performance across the board.
**Tech Stack:** Python 3.11, Playwright, SQLAlchemy 2.0, FastAPI, Pydantic Settings, pytest

---

## Summary of Changes by File

| File | Changes |
|------|---------|
| `src/config.py` | Add proxy fields, fix caching, fix model path default |
| `.env.example` | Add proxy vars, fix model path, remove unused Ollama keys |
| `src/logging_config.py` | **NEW** — centralized logging setup |
| `src/main.py` | Fix email extraction, fix cmd_run abort bug, fix draft logic, add proxy pass-through, remove vision imports |
| `src/discovery.py` | Accept browser/context, remove vision fallback, add proxy, add jitter/backoff |
| `src/website_auditor.py` | Accept browser/context, requests+BS4 fast path, cache results, single viewport, modern framework detection |
| `src/messenger.py` | Remove vision fallback from WhatsApp, disable auto-send (drafts only), add proxy |
| `src/researcher.py` | Remove LinkedIn scraping, use website enrichment, accept browser/context |
| `src/ai_engine.py` | Standardize model naming, remove 14B fallback, fix pitch cache (more fields or disable), fix save() duplicate |
| `src/membership_ideas.py` | Rewrite spa, doctor, fitness concepts |
| `src/dashboard.py` | SQL COUNT/GROUP BY for stats, pagination for /leads |
| `src/vision_mapper.py` | Remove __eid__ DOM mutation, use data attributes or coordinate mapping |
| `src/follow_up.py` | Add CANCELLED status to models, use it in cancel_sequence |
| `src/models.py` | Add CANCELLED to OutreachStatus |
| `src/summarizer.py` | Return data instead of printing |
| `requirements.txt` | Pin exact versions, add requests+beautifulsoup4 |
| `.gitignore` | Add data/, reports/, screenshots/, whatsapp_session/, *.db |
| `tests/` | Add tests for maturity analyzer, lead scorer, pitch validator, dashboard stats |

---

### Task 1: Infrastructure — Logging, Config, Requirements, Gitignore

**Files:**
- Create: `src/logging_config.py`
- Modify: `src/config.py`, `.env.example`, `requirements.txt`, `.gitignore`, `src/main.py` (add setup call)

- [ ] **Step 1: Create `src/logging_config.py`**
  ```python
  import logging
  import sys

  def setup_logging(level: int = logging.INFO) -> None:
      logging.basicConfig(
          level=level,
          format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
          handlers=[logging.StreamHandler(sys.stdout)],
      )
  ```

- [ ] **Step 2: Fix `src/config.py`**
  - Add proxy fields: `proxy_server: str = ""`, `proxy_username: str = ""`, `proxy_password: str = ""`
  - Fix `get_settings()` to use `@lru_cache` for real caching
  - Fix `local_model_path` default to match `.env.example` path structure (keep `/home/pranavvv/models/qwen3.5-VLM-9b/Qwen3.5-9B-Q4_K_M.gguf`)
  - Add `ollama_url: str = "http://localhost:11434"` and `ollama_model: str = "qwen2.5:9b"`

- [ ] **Step 3: Fix `.env.example`**
  - Fix `LOCAL_MODEL_PATH` to match config default
  - Add `PROXY_SERVER=`, `PROXY_USERNAME=`, `PROXY_PASSWORD=`
  - Keep OLLAMA_URL and OLLAMA_MODEL (now mapped in config)

- [ ] **Step 4: Fix `requirements.txt`**
  Pin versions and add new deps:
  ```
  playwright==1.49.0
  sqlalchemy==2.0.36
  fastapi==0.115.0
  uvicorn==0.32.0
  jinja2==3.1.4
  python-dotenv==1.0.1
  rich==13.9.0
  pydantic==2.9.0
  pydantic-settings==2.6.0
  python-multipart==0.0.17
  email-validator==2.2.0
  llama-cpp-python==0.3.0
  pillow==11.0.0
  requests==2.32.0
  beautifulsoup4==4.12.0
  ```
  Remove `httpx` (unused), `pytest` and `pytest-playwright` should ideally be dev deps but keep them for now.

- [ ] **Step 5: Fix `.gitignore`**
  Ensure it has:
  ```
  data/
  reports/
  screenshots/
  whatsapp_session/
  *.db
  ```

- [ ] **Step 6: Add logging setup to `src/main.py`**
  At module level after imports:
  ```python
  from src.logging_config import setup_logging
  setup_logging()
  ```

- [ ] **Step 7: Run tests to confirm no breakage**

---

### Task 2: Browser Pool — Shared Playwright Instance

**Files:**
- Create: `src/browser_pool.py`
- Modify: `src/discovery.py`, `src/website_auditor.py`, `src/messenger.py`, `src/researcher.py`, `src/main.py`

- [ ] **Step 1: Create `src/browser_pool.py`**
  ```python
  from __future__ import annotations
  from typing import Any
  from playwright.sync_api import Browser, BrowserContext, Playwright, sync_playwright
  from src.config import get_settings

  class BrowserPool:
      """Manage a single Playwright browser instance with optional proxy."""

      def __init__(self, headless: bool = True) -> None:
          self.headless = headless
          self._playwright: Playwright | None = None
          self._browser: Browser | None = None

      def _proxy_kwargs(self) -> dict[str, Any] | None:
          settings = get_settings()
          if not settings.proxy_server:
              return None
          proxy: dict[str, Any] = {"server": settings.proxy_server}
          if settings.proxy_username:
              proxy["username"] = settings.proxy_username
          if settings.proxy_password:
              proxy["password"] = settings.proxy_password
          return proxy

      def get_browser(self) -> Browser:
          if self._browser is None:
              self._playwright = sync_playwright().start()
              kwargs: dict[str, Any] = {"headless": self.headless}
              proxy = self._proxy_kwargs()
              if proxy:
                  kwargs["proxy"] = proxy
              self._browser = self._playwright.chromium.launch(**kwargs)
          return self._browser

      def new_context(self, viewport: dict[str, int] | None = None, user_agent: str | None = None) -> BrowserContext:
          browser = self.get_browser()
          kwargs: dict[str, Any] = {}
          if viewport:
              kwargs["viewport"] = viewport
          if user_agent:
              kwargs["user_agent"] = user_agent
          proxy = self._proxy_kwargs()
          if proxy:
              kwargs["proxy"] = proxy
          return browser.new_context(**kwargs)

      def close(self) -> None:
          if self._browser:
              self._browser.close()
              self._browser = None
          if self._playwright:
              self._playwright.stop()
              self._playwright = None

      def __enter__(self):
          return self

      def __exit__(self, exc_type, exc_val, exc_tb):
          self.close()
  ```

- [ ] **Step 2: Refactor `GoogleMapsScraper` in `src/discovery.py`**
  - Change `__init__` to accept optional `browser: Browser | None = None`
  - If `browser` is provided, use it; otherwise keep existing `sync_playwright()` behavior (for backward compat in tests)
  - Remove VisionAgent import and all vision fallback blocks (lines 96-105, 162-178)
  - Replace with logger.warning + continue / raise
  - Add exponential backoff with jitter when results are empty
  - Pass proxy through context if not using shared browser

- [ ] **Step 3: Refactor `WebsiteAuditor` in `src/website_auditor.py`**
  - Change `__init__` to accept optional `browser: Browser | None = None`
  - Add `requests` + `BeautifulSoup` fast path: try requests first, only launch Playwright if site uses heavy JS or requests fails
  - Reduce to one viewport check (desktop), infer mobile from viewport meta tag
  - Cache audit results: check DB or an in-module LRU cache before auditing
  - Add modern framework signatures (`__NEXT_DATA__`, `astro-island`, `data-reactroot`, `__VUE__`, `window.gatsby`)

- [ ] **Step 4: Refactor `WhatsAppSender` in `src/messenger.py`**
  - Accept optional `browser_pool: BrowserPool | None = None`
  - Remove all VisionAgent imports and vision fallback blocks (lines 116-148)
  - Replace auto-send with draft-only: `send()` method becomes private `_send()`; public API is `create_draft()`
  - Keep `ensure_auth()` for manual verification but add big warning comment

- [ ] **Step 5: Refactor `LinkedInResearcher` in `src/researcher.py`**
  - Accept optional `browser: Browser | None = None`
  - Remove `_scrape_linkedin()` entirely
  - Replace with `_enrich_from_website(lead, website_audit)` that scrapes the business's own /about, /services, homepage for description and services
  - Update `research()` to call new enrichment instead of LinkedIn

- [ ] **Step 6: Update `src/main.py` `run_pipeline()`**
  - Instantiate `BrowserPool` at top of `run_pipeline()`
  - Pass browser into `GoogleMapsScraper`, `WebsiteAuditor`, `LinkedInResearcher`
  - Close pool in finally block
  - Update `run_multi_pipeline()` to reuse the same pool across combos

- [ ] **Step 7: Run tests**

---

### Task 3: Remove VLM from Hot Path

**Files:**
- Modify: `src/discovery.py`, `src/messenger.py`, `src/vision_mapper.py`, `src/researcher.py`

- [ ] **Step 1: Remove vision fallback from `discovery.py`**
  - Delete consent vision fallback (lines 96-105)
  - Delete search vision fallback (lines 162-178)
  - When element not found: `logger.warning("... skipping"); continue`

- [ ] **Step 2: Remove vision fallback from `messenger.py`**
  - Delete all `VisionAgent` imports and usages
  - If chat input not found: raise `WhatsAppError("Chat input not found")`

- [ ] **Step 3: Remove vision fallback from `vision_mapper.py`**
  - Delete `_try_vision_fallback()` function
  - In `safe_fill` and `safe_click`: if selector not found, raise `PageMapError` immediately (no vision fallback)

- [ ] **Step 4: Remove vision fallback from `researcher.py`**
  - Already removed in Task 2

- [ ] **Step 5: Run tests**

---

### Task 4: Email Extraction Implementation

**Files:**
- Modify: `src/main.py`

- [ ] **Step 1: Replace `_extract_email_from_website()` stub**
  ```python
  import re
  import requests

  def _extract_email_from_website(website: str) -> str | None:
      if not website:
          return None
      if not website.startswith("http"):
          website = "https://" + website
      email_pattern = re.compile(r'[\w\.\-]+@[\w\.\-]+\.\w{2,}')
      for path in ["", "/contact", "/about", "/reach-us"]:
          try:
              url = website.rstrip("/") + path
              resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
              resp.raise_for_status()
              matches = email_pattern.findall(resp.text)
              for m in matches:
                  if not m.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                      return m
          except Exception:
              continue
      return None
  ```

- [ ] **Step 2: Run tests**

---

### Task 5: LinkedIn → Website Enrichment

**Files:**
- Modify: `src/researcher.py`

- [ ] **Step 1: Remove `_scrape_linkedin()` method entirely**

- [ ] **Step 2: Add `_enrich_from_website(lead, browser=None)`**
  ```python
  def _enrich_from_website(self, lead: Lead, browser=None) -> dict[str, Any]:
      result: dict[str, Any] = {"summary": "", "offerings": "", "years": None}
      if not lead.website:
          return result
      try:
          import requests
          from bs4 import BeautifulSoup
          url = lead.website if lead.website.startswith("http") else "https://" + lead.website
          resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
          soup = BeautifulSoup(resp.text, "html.parser")
          # Try meta description
          meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
          if meta:
              result["summary"] = meta.get("content", "").strip()
          # Try heading
          h1 = soup.find("h1")
          if h1 and not result["summary"]:
              result["summary"] = h1.get_text(strip=True)
          # Gather services from common sections
          for section in soup.find_all(["section", "div"]):
              cls = " ".join(section.get("class", [])).lower()
              if any(k in cls for k in ["service", "offer", "menu", "what we do", "treatment"]):
                  texts = [p.get_text(strip=True) for p in section.find_all(["p", "li"]) if len(p.get_text(strip=True)) > 10]
                  if texts:
                      result["offerings"] = "\n".join(texts[:5])
                      break
      except Exception as exc:
          logger.debug("Website enrichment failed for %s: %s", lead.business_name, exc)
      return result
  ```

- [ ] **Step 3: Update `research()` to call `_enrich_from_website()`**
  - Remove `linkedin_data = self._scrape_linkedin(lead)`
  - Add `web_data = self._enrich_from_website(lead)`
  - Use `web_data["summary"]` instead of `linkedin_data.get("summary")`
  - Use `web_data["offerings"]` instead of `linkedin_data.get("offerings")`
  - Remove `linkedin_url` from return dict

- [ ] **Step 4: Update tests in `tests/test_researcher.py`**

- [ ] **Step 5: Run tests**

---

### Task 6: Pitch Cache Fix

**Files:**
- Modify: `src/ai_engine.py`

- [ ] **Step 1: Fix `_hash_context()`**
  Include more fields so competitors don't get identical pitches:
  ```python
  key_data = {
      "name": ctx.name,
      "city": ctx.city,
      "type": ctx.business_type,
      "stage": ctx.maturity_stage,
      "score": ctx.website_score,
      "years": ctx.years_in_business,
      "has_website": ctx.has_website,
      "issues": ctx.website_issues,
      "rating": ctx.rating,
  }
  ```

- [ ] **Step 2: Fix `save()` to avoid duplicates**
  ```python
  def save(...):
      h = self._hash_context(ctx)
      existing = db.query(PitchCache).filter_by(context_hash=h).first()
      if existing:
          existing.pitch_text = pitch_text
          existing.membership_idea = membership_idea
          existing.website_benefits = website_benefits
          existing.model_used = model_used
          existing.last_used_at = _utc_now()
      else:
          cache = PitchCache(...)
          db.add(cache)
      db.commit()
  ```

- [ ] **Step 3: Remove `get()` side-effect commit**
  Replace `db.commit()` with `db.flush()` or just update without commit so caller controls transaction.

- [ ] **Step 4: Run tests**

---

### Task 7: Model Naming Standardization

**Files:**
- Modify: `src/ai_engine.py`, `src/config.py`

- [ ] **Step 1: Remove `_try_text_fallback()` and its call chain**
  The 14B fallback adds unnecessary complexity. If 9B works, use it. If not, template fallback is fine.

- [ ] **Step 2: Update `_try_primary()`**
  Use `self.settings.local_model_path` and `self.settings.vlm_mmproj_path` only.

- [ ] **Step 3: Update `_try_ollama_fallback()`**
  Use `self.settings.ollama_url` and `self.settings.ollama_model`.

- [ ] **Step 4: Run tests**

---

### Task 8: Dashboard Performance

**Files:**
- Modify: `src/dashboard.py`, `src/tracker.py`

- [ ] **Step 1: Add SQL-efficient stats function to `src/tracker.py`**
  ```python
  def get_outreach_stats(db: Session) -> dict[str, int]:
      from sqlalchemy import func
      from src.models import Outreach, OutreachStatus
      rows = db.query(Outreach.status, func.count(Outreach.id)).group_by(Outreach.status).all()
      stats = {"contacted": 0, "failed": 0, "responded": 0, "pending": 0}
      for status, count in rows:
          if status == OutreachStatus.SENT:
              stats["contacted"] = count
          elif status == OutreachStatus.FAILED:
              stats["failed"] = count
          elif status == OutreachStatus.RESPONDED:
              stats["responded"] = count
          elif status == OutreachStatus.PENDING:
              stats["pending"] = count
      return stats
  ```

- [ ] **Step 2: Update `index()` and `api_stats()` in `src/dashboard.py`**
  - Replace Python iteration with `get_outreach_stats(db)`
  - `stats["total"] = db.query(Lead).count()`

- [ ] **Step 3: Add pagination to `/leads`**
  ```python
  page: int = Query(1), per_page: int = Query(50)
  offset = (page - 1) * per_page
  all_leads = query.order_by(Lead.created_at.desc()).offset(offset).limit(per_page).all()
  ```

- [ ] **Step 4: Run tests**

---

### Task 9: Membership Ideas Differentiation

**Files:**
- Modify: `src/membership_ideas.py`

- [ ] **Step 1: Rewrite `spa` concept**
  Name: "Serenity Circle"
  Description: Focus on massage, wellness, aromatherapy packages
  Tiers: Relax (1 massage/month), Rejuvenate (2 treatments + sauna), Nirvana (unlimited wellness + nutrition)
  Remove all salon/haircut references

- [ ] **Step 2: Rewrite `doctor` concept**
  Name: "Premier Care Plan"
  Description: Private practice consultation models, preventive health
  Tiers: Individual (1 consultation + chat), Family (4 consults + health records), Concierge (home visits + priority)
  Different from clinic: focus on individual doctor practice, telemedicine, second opinions

- [ ] **Step 3: Rewrite `fitness` concept**
  Name: "Bootcamp Collective"
  Description: Class-based fitness (bootcamps, HIIT, yoga) — NOT equipment gym
  Tiers: Starter (4 classes/month), Pro (unlimited classes + nutrition), Elite (1-on-1 training + retreat)
  Different from gym: no equipment focus, community challenges, outdoor sessions

- [ ] **Step 4: Update `tests/test_membership_ideas.py`**

- [ ] **Step 5: Run tests**

---

### Task 10: Fix `__eid__` DOM Pollution

**Files:**
- Modify: `src/vision_mapper.py`

- [ ] **Step 1: Change JS walker to use data attribute instead of direct attribute**
  Replace `el.setAttribute("__eid__", String(eid))` with `el.dataset.eid = String(eid)`
  Update selector from `[__eid__='{idx}']` to `[data-eid='{idx}']`

- [ ] **Step 2: Add cleanup function**
  ```python
  def cleanup_page_map(page: Page) -> None:
      page.evaluate("""() => {
          document.querySelectorAll('[data-eid]').forEach(el => delete el.dataset.eid);
      }""")
  ```
  Call it after `build_page_map()` usage in discovery error handlers.

- [ ] **Step 3: Run tests**

---

### Task 11: Follow-up Status Fix

**Files:**
- Modify: `src/models.py`, `src/follow_up.py`, `tests/test_follow_up.py`

- [ ] **Step 1: Add `CANCELLED` to `OutreachStatus`**
  ```python
  CANCELLED = "cancelled"
  ```

- [ ] **Step 2: Update `cancel_sequence()` in `src/follow_up.py`**
  ```python
  .update({"status": OutreachStatus.CANCELLED})
  ```

- [ ] **Step 3: Update tests**

- [ ] **Step 4: Run tests**

---

### Task 12: Summarizer Separation of Concerns

**Files:**
- Modify: `src/summarizer.py`

- [ ] **Step 1: Change methods to return structured data instead of printing**
  Each method should return a dict or string. The CLI caller (`cmd_summary` in `main.py`) should do the `console.print()`.

- [ ] **Step 2: Update `cmd_summary` in `src/main.py`**
  Call `console.print()` on returned data.

- [ ] **Step 3: Run tests**

---

### Task 13: Add Missing Tests

**Files:**
- Create/Modify: `tests/test_maturity_analyzer.py`, `tests/test_lead_scorer.py`, `tests/test_pitch_validator.py`, `tests/test_dashboard_stats.py`

- [ ] **Step 1: Add `test_maturity_analyzer.py`**
  Test `MaturityAnalyzer.analyze()` with known inputs/outputs (startup vs established)

- [ ] **Step 2: Add `test_lead_scorer.py`**
  Test `LeadScorer.score()` edge cases (None years, no website, high reviews)

- [ ] **Step 3: Add `test_pitch_validator.py`**
  Test `PitchValidator.validate()` with good/bad pitches (too short, missing website reference)

- [ ] **Step 4: Add `test_dashboard_stats.py`**
  Test `get_outreach_stats()` with mock outreaches

- [ ] **Step 5: Run full test suite**

---

### Task 14: Prompt Template Fallback Verification

**Files:**
- Modify: `src/ai_engine.py`

- [ ] **Step 1: Verify `render_user()` already has fallback to `user_generic.txt`**
  It does (lines 121-123). Good.

- [ ] **Step 2: Add inline fallback if even generic template is missing**
  ```python
  except Exception:
      tmpl = self.env.get_template("user_generic.txt")
  ```
  Wrap in nested try/except:
  ```python
  try:
      tmpl = self.env.get_template(template_name)
  except Exception:
      try:
          tmpl = self.env.get_template("user_generic.txt")
      except Exception:
          return self._inline_generic_prompt(ctx)
  ```

- [ ] **Step 3: Add `_inline_generic_prompt()` method**
  Return a simple string prompt with all context variables.

- [ ] **Step 4: Run tests**

---

### Task 15: Final Integration & Verification

**Files:**
- All modified files

- [ ] **Step 1: Run full pytest suite**
  ```bash
  python -m pytest tests/ -v --tb=short
  ```

- [ ] **Step 2: Fix any failing tests**

- [ ] **Step 3: Run mypy or basic import check**
  ```bash
  python -c "from src.main import main; from src.dashboard import app; print('OK')"
  ```

- [ ] **Step 4: Commit all changes**

---

## Execution Order

1. **Task 1** (Infrastructure) — Must be first; other tasks depend on config/logging
2. **Task 2** (Browser Pool) + **Task 3** (Remove VLM) — Do together; they touch the same files
3. **Task 4** (Email extraction) — Independent
4. **Task 5** (LinkedIn → Website) — Independent after Task 2
5. **Task 6** (Pitch cache) + **Task 7** (Model naming) — Touch same file; do together
6. **Task 8** (Dashboard) — Independent
7. **Task 9** (Membership ideas) — Independent
8. **Task 10** (__eid__) — Independent
9. **Task 11** (Follow-up status) — Independent
10. **Task 12** (Summarizer) — Independent
11. **Task 14** (Prompt fallback) — Independent
12. **Task 13** (Tests) — Do after all implementation
13. **Task 15** (Final verification)

## Risk Mitigation

- **Backward compatibility:** Every class keeps optional `browser` param; if not passed, old behavior works
- **Tests:** Run after every task; fix immediately
- **Breaking changes:** `WhatsAppSender.send()` will change signature — update callers in `main.py`
- **DB migration:** Adding `CANCELLED` enum value works with SQLite (string-backed); no Alembic needed
