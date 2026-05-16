# Browser Automation Hang Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:systematic-debugging and superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the Google Maps scraper (and downstream WhatsApp/Messenger flows) so the browser opens, navigates, interacts, and completes instead of hanging or appearing to do nothing.

**Architecture:** Playwright-based browser automation with vision-language model (VLM) fallbacks. The scraper opens a headed Chromium, navigates to Google Maps, handles consent, searches, scrolls results, and extracts business cards. WhatsApp messenger opens WhatsApp Web, authenticates, and sends messages.

**Tech Stack:** Python, Playwright (sync API), Pillow (screenshots), local GGUF / Ollama VLM.

---

## Root Cause Diagnosis

### Phase 1: Evidence

- User reports: "browser starts but nothing happens after that"
- Screenshot directory contains `error_*.png` files (~685KB each) and `page_map_*.txt` files, proving `DiscoveryError` IS being raised
- Previous fix changed `wait_until="domcontentloaded"` → `"networkidle"` in `discovery.py:54`
- Google Maps establishes persistent WebSocket / analytics connections; `networkidle` can hang for 30s+ or never fire
- When `goto()` times out, the entire `discover()` method raises `DiscoveryError`, browser closes, pipeline exits with 0 leads
- Vision fallback screenshots (`step_01_*.png`) are tiny (~26KB) suggesting VLM fallback runs on partially-loaded pages

### Phase 2: Hypothesis

**Primary:** `page.goto(wait_until="networkidle")` hangs on Google Maps because persistent WebSocket connections prevent the 500ms idle window from occurring.

**Secondary:** After `goto()` the Maps JS app may not have rendered the search box yet; the scraper tries to interact immediately and fails, falling back to VLM which also fails because the page isn't ready.

**Tertiary:** Google Maps DOM selectors (`input[id="searchboxinput"]`, `div[role="feed"]`, `div.fontHeadlineSmall`) may be outdated.

**Quaternary:** No structured logging at component boundaries makes it impossible for the user to see where execution stops.

---

## Tasks

### Task 1: Fix Google Maps navigation wait strategy

**Files:**
- Modify: `src/discovery.py:52-56`

**Change:**
1. Revert `wait_until="networkidle"` to `"domcontentloaded"`
2. After `goto()`, explicitly wait for the search box to appear using `page.wait_for_selector('input[id="searchboxinput"]', timeout=30000)`
3. If the primary selector times out, try a broader selector chain as fallback before raising

**Why:** `domcontentloaded` guarantees the DOM is parsed. The explicit element wait guarantees the Maps app has rendered the search UI. This avoids the `networkidle` WebSocket hang.

---

### Task 2: Add structured logging to discovery boundaries

**Files:**
- Modify: `src/discovery.py:51-212`

**Change:**
1. Add `import logging` and `logger = logging.getLogger(__name__)`
2. Log at each major boundary:
   - "Navigating to Google Maps"
   - "Handling consent dialog"
   - "Searching for: {query}"
   - "Waiting for results"
   - "Found {N} result cards"
   - "Extracted {N} leads"
   - "Scraping failed: {exc}" (in except block)

**Why:** The user cannot tell whether the code hangs at navigation, consent, search, or results. Logging makes the failure point explicit.

---

### Task 3: Harden consent dialog handling

**Files:**
- Modify: `src/discovery.py:58-85`

**Change:**
1. After clicking a consent button, break BOTH loops (use a flag or refactor to `while` with early return)
2. Add a short `page.wait_for_timeout(1000)` after clicking to let the dialog animate out
3. Add an additional text variant: `"I agree"` and `"Use without accepting"` which appear on newer Google consent screens
4. Add a `page.wait_for_selector` guard after consent: wait for `input[id="searchboxinput"]` before proceeding

**Why:** The current double-loop `break` only breaks the inner loop, causing 2 extra iterations. Missing text variants cause the dialog to remain unhandled. A lingering dialog blocks all subsequent interaction.

---

### Task 4: Modernize Google Maps result selectors

**Files:**
- Modify: `src/discovery.py:112-141` and `_extract_card`

**Change:**
1. Expand `CARD_SELECTORS` to include current Google Maps result list patterns:
   - `'div[role="feed"] > div'`
   - `'div[role="main"] div[data-result-index]'`
   - `'a[href*="/maps/place"]'`
   - `'div[role="listitem"]'`
   - `'[data-result-index]'`
2. In `_extract_card`, add fallback for name: try `[data-value="Business name"]` or `h1`, `h2`, `h3` if `div.fontHeadlineSmall` is not found
3. In `_extract_card`, add fallback for address: try `button[data-item-id="address"]` or any `span`/`div` containing a street number pattern

**Why:** Google Maps changes CSS classes frequently. Relying on a single class name (`fontHeadlineSmall`) causes 100% extraction failure when the class changes.

---

### Task 5: Fix safe_fill exception swallowing

**Files:**
- Modify: `src/discovery.py:88-109`

**Change:**
1. Wrap `safe_fill()` and `page.keyboard.press("Enter")` in their own `try/except` inside the fallback block
2. If the fallback also fails, log the error and raise a clear `DiscoveryError("Search failed: could not locate or fill the Google Maps search box")`

**Why:** Currently, if `safe_fill()` raises `PageMapError`, it propagates out of the `except Exception` block, bypassing all context. A nested try/except catches it and provides a meaningful error message.

---

### Task 6: Verify fixes with targeted unit tests

**Files:**
- Modify: `tests/test_discovery.py`

**Change:**
1. Add test that mocks `page.goto` with `wait_until="domcontentloaded"` and verifies `wait_for_selector` is called for the search box
2. Add test that verifies `DiscoveryError` is raised with a clear message when all search box locators fail
3. Ensure existing tests still pass after selector changes

---

### Task 7: Add similar logging to WhatsApp messenger

**Files:**
- Modify: `src/messenger.py:81-140`

**Change:**
1. Add logging at key steps: "Navigating to WhatsApp Web", "Checking for invalid number", "Waiting for chat input", "Typing message", "Sending message"
2. Ensure `input_box` is redefined after vision fallback before trying to type/send

**Why:** The user experiences the same "browser opens but nothing happens" with WhatsApp. Logging makes the hang point visible.

---

## Execution Order

1. Task 1 (navigation wait) — highest impact, single-line change
2. Task 2 (logging) — makes all subsequent debugging visible
3. Task 3 (consent handling) — prevents blocking dialogs
4. Task 5 (safe_fill exception) — prevents silent failure cascade
5. Task 4 (selectors) — fixes extraction after navigation works
6. Task 7 (WhatsApp logging) — parallel improvement for messenger
7. Task 6 (tests) — regression coverage
