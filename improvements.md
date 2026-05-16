# Client Acquisition System — Master Improvement Plan

> **Vision:** Transform the current pipeline from a "send-and-hope" outreach tool into an **intelligent client acquisition engine** that analyzes businesses deeply, proposes high-value digital strategies tailored to their maturity and category, and closes deals through value-first education rather than cold pitches.
>
> **Methodology:** Superpowers-driven planning + brainstorming + subagent-driven deployment. Each phase is designed to be implemented by focused subagent workers.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Phase 1: The AI Consistency & Reliability Engine](#2-phase-1-the-ai-consistency--reliability-engine)
3. [Phase 2: Smart Business Intelligence Framework](#3-phase-2-smart-business-intelligence-framework)
4. [Phase 3: Value-First Pitch System (Membership & Loyalty Ideas)](#4-phase-3-value-first-pitch-system-membership--loyalty-ideas)
5. [Phase 4: Automation, Follow-Up & CRM Evolution](#5-phase-4-automation-follow-up--crm-evolution)
6. [Phase 6: Subagent-Driven Deployment Architecture](#6-phase-6-subagent-driven-deployment-architecture)
7. [Implementation Roadmap](#7-implementation-roadmap)

---

## 1. Executive Summary

### Current State
The system discovers businesses on Google Maps, scrapes LinkedIn for basic context, runs a local VLM (Qwen 3.5 9B) to generate a generic "website development" pitch, and sends it via email or WhatsApp. It tracks outcomes in a SQLite database with a FastAPI dashboard.

### Critical Gaps
| Gap | Impact |
|-----|--------|
| AI pitch generation is inconsistent — same business can get wildly different pitches across runs | Destroys trust, looks unprofessional |
| No business maturity analysis — a 20-year-old cafe and a 3-month-old cafe get the same pitch | Misses the actual pain points of each business |
| Pitches are feature-focused ("we'll build you a website") not outcome-focused ("here's how you'll make more money") | Low conversion rate |
| No follow-up automation — if they don't reply, lead goes cold | Wasted discovery effort |
| No differentiated value propositions per business type — cafe pitch is basically salon pitch with words swapped | Businesses see through generic templates instantly |
| Dashboard is read-only — cannot edit pitches, cannot trigger follow-ups, cannot mark responses | Operational friction |
| Vision agent fallbacks are slow and error-prone — VLM inference on every fallback adds minutes per lead | Pipeline bottlenecks |

### Target State
An autonomous acquisition engine where:
- **AI produces consistent, high-quality outputs** through prompt engineering, structured generation, and output validation
- **Every pitch is a business strategy consultation** — analyzing years-in-business, website audit, and competitor positioning to propose specific digital transformations
- **Membership & loyalty concepts are auto-generated per business category** — cafés get "Coffee Club," salons get "VIP Beauty Pass," clinics get "Family Health Plans"
- **The system runs itself** — batch mode, smart follow-ups, response parsing, and deal-stage tracking
- **Subagents handle implementation** — each improvement module is a deployable subagent task

---

## 2. Phase 1: The AI Consistency & Reliability Engine

### 2.1 Problem Diagnosis

The current AI stack (`researcher.py` → `_generate_with_llama_cpp`) has multiple consistency killers:

1. **Temperature 0.7** — too high for structured business pitches; causes creative drift
2. **No output schema enforcement** — parses raw text with `json.loads()`; VLM often emits malformed JSON, markdown wrappers, or extra commentary
3. **No retry / self-correction loop** — one shot, then fallback to generic template
4. **No prompt versioning** — cannot A/B test what works
5. **Context window is underutilized** — LinkedIn summary is truncated to 500 chars, website audit details are minimal
6. **Single-model dependency** — if Qwen 3.5 9B is unavailable, entire pipeline degrades to generic fallback

### 2.2 The Consistency Stack

#### Layer A: Structured Generation with Grammar Constraints

Replace free-form JSON generation with **GBNF grammar-constrained output** (llama-cpp-python supports `grammar` parameter). This guarantees valid JSON every single time.

```python
# src/researcher.py — new constant
PITCH_GRAMMAR = r'''
root ::= "{" ws "\"pitch_text\"" ":" ws string "," ws "\"context_summary\"" ":" ws string "," ws "\"membership_idea\"" ":" ws string "," ws "\"website_benefits\"" ":" ws string "}"
ws ::= [ \t\n]*
string ::= "\"" ([^"\\] | "\\" ["\\/bfnrt] | "\\u" [0-9a-fA-F]{4})* "\""
'''
```

**Impact:** Eliminates 90%+ of JSON parse failures. The VLM cannot hallucinate extra keys or broken syntax.

#### Layer B: Temperature Scheduling

| Stage | Temperature | Why |
|-------|-------------|-----|
| Business analysis / fact extraction | 0.1 | Factual, deterministic |
| Pitch generation (first draft) | 0.3 | Creative but controlled |
| Pitch refinement / editing | 0.5 | Allows stylistic variation |
| Membership idea generation | 0.4 | Needs creativity within constraints |

Implement a `TemperatureScheduler` class in `src/ai_engine.py`.

#### Layer C: Prompt Templates as Versioned Assets

Move all prompts from inline strings in `researcher.py` to **versioned Jinja2 templates** in `src/prompts/`:

```
src/prompts/
  ├── v1/
  │   ├── system_pitch.txt
  │   ├── user_cafe.txt
  │   ├── user_salon.txt
  │   ├── user_retail.txt
  │   ├── user_clinic.txt
  │   ├── user_restaurant.txt
  │   └── user_generic.txt
  └── v2/  (for A/B testing)
```

Each template receives a rich `BusinessContext` dataclass:

```python
# src/models.py — new dataclass
@dataclass
class BusinessContext:
    name: str
    city: str
    business_type: str
    years_in_business: int | None
    has_website: bool
    website_score: str  # "good", "needs_work", "poor", "none"
    website_issues: list[str]
    linkedin_summary: str
    offerings: str
    competitors_nearby: list[str]  # new: scraped from Maps
    peak_hours_hint: str | None    # new: from Maps "popular times"
    customer_capacity: str | None  # new: "small", "medium", "large"
```

#### Layer D: The Validation & Retry Loop

```python
# src/ai_engine.py — new module
class PitchValidator:
    SCHEMA = {
        "pitch_text": {"type": "string", "min_length": 100, "max_length": 800},
        "context_summary": {"type": "string", "min_length": 20},
        "membership_idea": {"type": "string", "min_length": 50},
        "website_benefits": {"type": "string", "min_length": 50},
    }

    def validate(self, output: dict) -> list[str]:
        """Return list of validation errors; empty list means pass."""
        errors = []
        for key, rules in self.SCHEMA.items():
            val = output.get(key, "")
            if len(val) < rules.get("min_length", 0):
                errors.append(f"{key} too short ({len(val)} chars)")
            if len(val) > rules.get("max_length", 9999):
                errors.append(f"{key} too long ({len(val)} chars)")
        # Content guards
        if "website" not in output.get("pitch_text", "").lower():
            errors.append("pitch_text missing 'website' keyword")
        return errors
```

The generation flow becomes:
1. Generate with grammar + low temp
2. Validate output
3. If validation fails, feed errors back as context and retry (max 3 retries)
4. If all retries fail, use fallback — but **log the failure pattern** for prompt improvement

#### Layer E: Multi-Model Fallback Chain

```python
# src/ai_engine.py
MODEL_CHAIN = [
    ("local_vlm", "qwen3.5-vlm-9b"),      # primary
    ("local_text", "qwen2.5-14b"),        # text-only, larger context
    ("ollama_api", "qwen2.5:32b"),        # if Ollama is running remotely
    ("template", None),                    # final fallback
]
```

Each model gets the same prompt. If primary fails validation, try next. This makes the system **anti-fragile**.

#### Layer F: Output Caching & Deduplication

Cache successful pitch generation by `(business_type, website_score, years_in_business_bucket)`:

```python
# SQLite cache table
class PitchCache(Base):
    __tablename__ = "pitch_cache"
    id = mapped_column(Integer, primary_key=True)
    context_hash = mapped_column(String(64), index=True)  # SHA256 of BusinessContext
    pitch_text = mapped_column(Text)
    membership_idea = mapped_column(Text)
    website_benefits = mapped_column(Text)
    model_used = mapped_column(String(50))
    created_at = mapped_column(DateTime, default=_utc_now)
```

A café with a poor website, 5 years in business, in Mumbai — if generated once, reuse the template with name/address swap for 30 days.

### 2.3 Implementation Tasks (Subagent-Ready)

| Task | Subagent | Files |
|------|----------|-------|
| T1.1 Create `src/ai_engine.py` with grammar-constrained generation, temperature scheduler, validation loop, multi-model chain | `coder` | New file |
| T1.2 Create `src/prompts/` Jinja2 template system with v1 templates per business type | `coder` | New dir |
| T1.3 Add `PitchCache` model to `src/models.py`, migrate DB | `coder` | `models.py`, `database.py` |
| T1.4 Refactor `researcher.py` to use `ai_engine.py` instead of direct llama-cpp calls | `coder` | `researcher.py` |
| T1.5 Add comprehensive tests for validation loop and cache hits | `coder` | `test_ai_engine.py` |

---

## 3. Phase 2: Smart Business Intelligence Framework

### 3.1 The Maturity-Adjusted Analysis Model

A business's **years in operation** is the single strongest predictor of its digital needs. The current system extracts `years_in_business` but barely uses it. We will build a **Maturity Matrix** that drives every pitch decision.

#### Maturity Matrix

| Years | Stage | Psychology | Digital Need | Price Sensitivity |
|-------|-------|------------|--------------|-------------------|
| 0–1 | **Startup** | Hustling, budget-conscious, needs validation | Social proof, landing page, Google Business Profile optimization | Very high |
| 2–5 | **Growth** | Establishing reputation, first employees | Booking system, menu/services online, reviews aggregation | High |
| 5–15 | **Established** | Proven model, owner is busy, competitors catching up | Automation, loyalty program, SEO, online ordering | Medium |
| 15+ | **Legacy** | Owner may be tech-averse, "we've survived without it" | Modernization without disruption, staff training, gradual migration | Low (but high resistance) |

#### Scraping Enhancements for Richer Context

Enhance `discovery.py` and `researcher.py` to extract:

1. **Review count & rating** from Google Maps (social proof indicator)
2. **Price level** ($ to $$$$) — indicates target customer segment
3. **Popular times** — indicates peak capacity constraints
4. **Photos count** — indicates how visual the business is
5. **Competitors on the same street** — scraped from nearby results
6. **Website tech stack** — already partially done in `website_auditor.py`, expand to detect:
   - WordPress (old vs new)
   - Wix / Squarespace / Shopify (DIY builders = ready to upgrade)
   - No website at all
   - Social media only (Instagram/Facebook link but no domain)

#### The Business Report Card

Before any pitch is sent, generate an internal `BusinessReportCard`:

```python
@dataclass
class BusinessReportCard:
    business_name: str
    maturity_stage: str  # startup, growth, established, legacy
    digital_readiness: int  # 1-10 score
    biggest_pain_point: str  # derived from maturity + audit
    competitor_gap: str  # what competitors have that they don't
    estimated_monthly_revenue_tier: str  # inferred from price level + reviews
    recommended_strategy: str  # website-only, website+seo, full digital transformation
    projected_roi_months: int  # how many months to pay back website investment
```

**Example inference rules:**
- Café, 12 years, 4.2★, 200 reviews, no website → **Legacy + invisible online**. Pain: younger customers can't find them. Strategy: Modern site + Google SEO + online menu. ROI: 2-3 months.
- Salon, 2 years, 4.8★, 50 reviews, Wix site → **Growth + DIY ceiling**. Pain: looks amateur vs competitors. Strategy: Professional redesign + booking integration. ROI: 1-2 months.
- Restaurant, 6 months, no reviews, no website → **Startup + unknown**. Pain: needs validation and visibility. Strategy: Landing page + Google Business + Instagram link. ROI: 3-4 months.

### 3.2 Website Benefit Framework (Per Maturity Stage)

Instead of generic "modern responsive website," the pitch must articulate **specific benefits tied to their stage**:

#### For Startups (0–1 years)
- "Your website is your 24/7 storefront before word-of-mouth kicks in"
- "Collect customer emails from day one — your most valuable asset"
- "Google Business Profile + website = you show up when someone searches 'café near me'"
- "One professional page builds more trust than 50 Instagram posts"

#### For Growth (2–5 years)
- "You're losing bookings to competitors with online reservation systems"
- "Your staff spends 30 mins/day answering 'are you open?' — a website answers it instantly"
- "Every Instagram follower should be able to click to your menu in 1 tap"
- "Online reviews on your own site = you control the narrative"

#### For Established (5–15 years)
- "You've built the reputation — now let the website work while you sleep"
- "Your regulars are aging; their kids search on Google, not memory"
- "A loyalty program integrated into your site increases visit frequency by 20-30%"
- "Online pre-orders for peak hours = smoother operations + higher ticket size"

#### For Legacy (15+ years)
- "Your competitors are retiring too — the ones with websites are selling to younger owners"
- "Your staff can learn one simple system — we train them"
- "Keep your phone number, keep your routines, just add a digital front door"
- "When you decide to sell, a business with a website sells for 20-40% more"

### 3.3 Implementation Tasks (Subagent-Ready)

| Task | Subagent | Files |
|------|----------|-------|
| T2.1 Enhance `GoogleMapsScraper` to extract rating, review count, price level, photo count | `coder` | `discovery.py` |
| T2.2 Enhance `WebsiteAuditor` to detect Wix/Squarespace/Shopify/WordPress and DIY builders | `coder` | `website_auditor.py` |
| T2.3 Create `src/business_intelligence.py` with `MaturityAnalyzer` and `BusinessReportCard` | `coder` | New file |
| T2.4 Update prompt templates to inject maturity stage and specific benefits | `coder` | `src/prompts/` |
| T2.5 Add review/rating/price fields to `Lead` model | `coder` | `models.py` |

---

## 4. Phase 3: Value-First Pitch System (Membership & Loyalty Ideas)

### 4.1 The Philosophy Shift

**Stop selling websites. Start selling business outcomes that happen to require a website.**

The membership/loyalty ideas are not add-ons. They are **the hook** that makes the website pitch irresistible. Every business type gets a tailored "digital loyalty concept" that:
1. Costs the customer a small monthly fee
2. Saves them money or gives them status
3. **Requires a website/backend to manage** (this is why they need us)

### 4.2 Business-Type-Specific Membership & Digital Concepts

#### ☕ Café / Coffee Shop

**Concept: "The Regulars Club"**

| Tier | Monthly Price | Benefits |
|------|--------------|----------|
| **Espresso** | ₹299 / $4 | 1 free coffee daily, 10% off food, priority seating |
| **Barista** | ₹599 / $8 | Everything above + 2 free pastries/week, 1 free guest coffee/day, reserved table for 2 hrs |
| **Roaster** | ₹999 / $12 | Everything above + unlimited wifi lounge access 4 hrs/day, invites to tasting events, name on "Founders Wall" |

**Website Integration Needed:**
- Member login portal to track credits
- QR code scan at counter for instant verification
- WhatsApp bot for "renewal reminder" and "your coffee is ready"
- Admin dashboard for owner: active members, monthly recurring revenue, most popular time slots

**Pitch Angle:**
> "With just 50 Regulars Club members at the Espresso tier, you generate ₹14,950/month in predictable revenue — that's enough to cover your rent. The website manages sign-ups, payments, and QR check-ins automatically. You're not just selling coffee; you're selling belonging."

---

#### 💇 Salon / Spa

**Concept: "Glow Pass"**

| Tier | Monthly Price | Benefits |
|------|--------------|----------|
| **Glow** | ₹799 / $10 | 1 free basic service/month (facial/haircut), 15% off all services |
| **Radiance** | ₹1,499 / $18 | 2 premium services/month, 20% off products, priority weekend booking |
| **Platinum** | ₹2,999 / $35 | Unlimited basic services, 1 free premium/month, 25% off products, personal stylist chat |

**Website Integration Needed:**
- Online booking with member-only time slots
- Service credit tracker
- Product e-commerce with member discounts
- Before/after gallery (members consent to feature)

**Pitch Angle:**
> "Your busiest hours are weekends, but weekdays are empty. Glow Pass members get priority weekend slots — creating scarcity. Meanwhile, their 'free monthly service' brings them in on Tuesdays and Wednesdays. The website handles bookings, credit tracking, and even reminds members 'your monthly facial is waiting.'"

---

#### 🏥 Clinic / Medical Practice

**Concept: "Family Health Plan"**

| Tier | Monthly Price | Benefits |
|------|--------------|----------|
| **Individual** | ₹499 / $6 | 1 free consultation/month, 10% off diagnostics, 24hr chat with nurse |
| **Family (4)** | ₹1,299 / $16 | 4 consultations/month, 15% off diagnostics, priority appointment booking, vaccination tracker |
| **Senior Care** | ₹999 / $12 | 2 home-visit eligible consults/month, medicine reminders via WhatsApp, emergency hotline |

**Website Integration Needed:**
- Patient portal with medical history (HIPAA/GDPR compliant structure)
- Appointment booking with doctor preference
- WhatsApp reminder bot for medications and appointments
- Family account linking (parent manages kids + elderly parents)

**Pitch Angle:**
> "A family of four visiting twice a year generates ₹4,000. A Family Health Plan member pays ₹1,299/month = ₹15,588/year. That's 4x revenue per family — and the website manages consent forms, appointment history, and automatic WhatsApp reminders so your front desk isn't making 50 calls a day."

---

#### 🍽️ Restaurant

**Concept: "Chef's Table Circle"**

| Tier | Monthly Price | Benefits |
|------|--------------|----------|
| **Diner** | ₹699 / $9 | 1 complimentary appetizer per visit, 10% off bill, skip-the-wait list |
| **Gourmet** | ₹1,299 / $16 | 1 complimentary main course/month, 15% off, reserved table Fridays, birthday surprise dish |
| **Connoisseur** | ₹2,499 / $30 | Tasting menu preview access, chef meet-and-greet quarterly, 20% off, private dining priority |

**Website Integration Needed:**
- Reservation system with member priority
- Pre-order for tasting events (limited seats = FOMO)
- Review collection system (members who review get bonus credits)
- Inventory-aware menu (hides items when 86'd)

**Pitch Angle:**
> "Your best customers come twice a month. Chef's Table Circle turns them into members who come weekly — because they've already paid. The reservation system gives them priority, so they never hear 'fully booked.' Your website becomes a revenue engine, not a brochure."

---

#### 🛍️ Retail Shop

**Concept: "Insider Circle"**

| Tier | Monthly Price | Benefits |
|------|--------------|----------|
| **Insider** | ₹399 / $5 | Early access to new stock, 10% off, free delivery |
| **VIP** | ₹899 / $11 | Everything above + 20% off, personal shopper chat, exclusive colorways |
| **Founder** | ₹1,999 / $25 | Everything above + quarterly surprise box, name in store credits, invite-only sales |

**Website Integration Needed:**
- Members-only product drops (password-protected catalog pages)
- Wishlist + back-in-stock alerts
- WhatsApp broadcast for "insider drops"
- Loyalty points tracker

**Pitch Angle:**
> "Right now, a customer buys once and forgets you. Insider Circle creates 'drop culture' — members check your site every Tuesday for new stock because they get first dibs. The website manages access tiers, sends WhatsApp alerts, and tracks points automatically."

---

#### 🏋️ Gym / Fitness Center

**Concept: "Fit Squad"**

| Tier | Monthly Price | Benefits |
|------|--------------|----------|
| **Starter** | ₹999 / $12 | 1 personal training session/month, nutrition guide access, class booking |
| **Pro** | ₹1,999 / $24 | 4 PT sessions/month, body composition tracking, priority class booking |
| **Elite** | ₹3,999 / $48 | Unlimited PT, recovery lounge access, guest passes, branded merchandise |

**Website Integration Needed:**
- Class schedule with real-time capacity
- Progress dashboard (weight, measurements, attendance streak)
- Diet plan portal
- Community forum (members only)

---

#### 📚 Tuition Center / Coaching

**Concept: "Scholar's Path"**

| Tier | Monthly Price | Benefits |
|------|--------------|----------|
| **Learner** | ₹799 / $10 | 1 extra doubt session/week, recorded class access, practice tests |
| **Achiever** | ₹1,499 / $18 | Everything above + 1-on-1 monthly review, study material library, parent progress reports |
| **Topper** | ₹2,499 / $30 | Everything above + daily mentorship check-in, mock exam series, career counseling |

**Website Integration Needed:**
- Student portal with video library
- Test scoring dashboard
- Parent login for progress tracking
- Automated report cards

---

### 4.3 The Pitch Structure (Template)

Every pitch now follows this **4-part structure**:

```
1. THE INSIGHT (1 sentence)
   "I noticed [Business Name] has been serving [City] for [X] years, but [specific gap]."

2. THE OPPORTUNITY (1-2 sentences)
   "Businesses like yours typically [maturity-specific benefit]. With [specific feature], you could [outcome]."

3. THE CONCEPT (2-3 sentences)
   "We could build you a [Membership Name] program where customers pay [price]/month for [top 2 benefits]. 
    This runs entirely through your website — sign-ups, payments, QR check-ins, and WhatsApp reminders."

4. THE ASK (1 sentence)
   "Would you be open to a 15-minute call where I show you how this would look for [Business Name]?"
```

### 4.4 Implementation Tasks (Subagent-Ready)

| Task | Subagent | Files |
|------|----------|-------|
| T3.1 Create `src/membership_ideas.py` with concept library per business type | `coder` | New file |
| T3.2 Update Jinja2 prompt templates to include membership concept injection | `coder` | `src/prompts/` |
| T3.3 Add `membership_idea` and `website_benefits` fields to `Lead` model and outreach tracking | `coder` | `models.py`, `tracker.py` |
| T3.4 Create mock pitch examples for each business type and run validation | `coder` | Tests + docs |

---

## 5. Phase 4: Automation, Follow-Up & CRM Evolution

### 5.1 Follow-Up Sequences

Currently, if a lead doesn't reply, they are forgotten. Implement **smart follow-up sequences**:

| Day | Channel | Message Type | Condition |
|-----|---------|--------------|-----------|
| 0 | Email/WhatsApp | Initial pitch | — |
| 3 | WhatsApp | "Quick follow-up — did my message about [Membership Name] reach you?" | No reply |
| 7 | Email | Value-first: "3 cafés in [City] that doubled revenue with loyalty programs" | No reply |
| 14 | WhatsApp | "Last message from me — here's a 2-min video of how the [Concept] works" | No reply |
| 30 | Email | "Monthly digital tips for [business type] owners" (newsletter opt-in) | Still no reply |

**Implementation:**
- New `FollowUpSequence` model in `models.py`
- Scheduled runner (can be a cron job or APScheduler) that checks pending follow-ups
- Each follow-up message is **re-generated by AI** with fresh context (not static templates)

### 5.2 Response Parsing & Intent Detection

When a lead replies, the system should classify the intent:

```python
class ReplyIntent(str, Enum):
    INTERESTED = "interested"      # "Tell me more", "What's the cost?"
    PRICE_INQUIRY = "price_inquiry" # "How much?", "Pricing?"
    NOT_NOW = "not_now"            # "Maybe later", "Busy right now"
    NOT_INTERESTED = "not_interested" # "No thanks", "Unsubscribe"
    BOOKED = "booked"              # "Call me Tuesday 3pm"
    SPAM = "spam"                  # Gibberish
```

Use a lightweight classifier (can be regex + keyword for v1, local LLM for v2) to:
1. Auto-tag the reply in the dashboard
2. Send an alert to the user (email/telegram) for "INTERESTED" or "PRICE_INQUIRY"
3. Auto-reply to "PRICE_INQUIRY" with a pre-written pricing guide
4. Move "BOOKED" leads to a "Hot Leads" priority queue

### 5.3 Dashboard CRM Upgrades

Transform the read-only dashboard into an **actionable CRM**:

| Feature | Description |
|---------|-------------|
| **Lead Scoring** | Auto-score leads 1-100 based on maturity + engagement + reply intent |
| **Kanban Board** | Drag leads: Cold → Pitched → Replied → Meeting Booked → Closed → Lost |
| **Note Taking** | Add manual notes per lead (e.g., "Owner is Amit, prefers WhatsApp, busy mornings") |
| **Task Reminders** | "Call Café Largo tomorrow at 11am" |
| **Revenue Forecast** | Based on pipeline stage probabilities |
| **Bulk Actions** | Select 10 leads → "Send follow-up #2" |
| **Template Library** | Save winning pitches as reusable templates |

### 5.4 Batch Mode & Headless Operation

Add a `batch` command to `main.py`:

```bash
python -m src.main batch \
  --city Mumbai \
  --category cafe \
  --max-leads 50 \
  --auto-send \
  --follow-up-sequence standard \
  --channels email
```

This enables:
- Running overnight
- A/B testing at scale
- Serving multiple cities in parallel

### 5.5 Implementation Tasks (Subagent-Ready)

| Task | Subagent | Files |
|------|----------|-------|
| T4.1 Create `src/follow_up.py` with sequence engine and scheduler integration | `coder` | New file |
| T4.2 Create `src/reply_parser.py` with intent classification | `coder` | New file |
| T4.3 Add `FollowUp`, `LeadNote`, `LeadScore` models | `coder` | `models.py` |
| T4.4 Upgrade dashboard with Kanban, notes, bulk actions, lead scoring | `coder` | `dashboard.py` + templates |
| T4.5 Add `batch` CLI command to `main.py` | `coder` | `main.py` |
| T4.6 Add notification system (email/telegram) for hot leads | `coder` | New file |

---

## 6. Phase 6: Subagent-Driven Deployment Architecture

### 6.1 The Superpowers Framework

The project already has `docs/superpowers/` and `docs/superpowers/plans/`. We will formalize this into a **subagent orchestration system** where each improvement phase is a deployable plan executed by specialized subagents.

#### Subagent Types

| Subagent | Role | When to Deploy |
|----------|------|----------------|
| `explorer` | Read-only codebase analysis, dependency mapping | Before any refactor |
| `planner` | Architecture design, task decomposition, spec writing | Before implementation |
| `coder` | Code writing, testing, debugging | During implementation |
| `reviewer` | Code review, test validation, spec compliance | After implementation |

#### The Deployment Loop

```
1. PLANNER reads improvements.md section → writes detailed task plan to docs/superpowers/plans/YYYY-MM-DD-{task}.md
2. EXPLORER validates the plan against current codebase → flags conflicts
3. CODER implements task-by-task with tests
4. REVIEWER validates against spec → approves or requests changes
5. Merge to main, update improvements.md status
```

### 6.2 Configuration for Subagent Safety

Create `.windsurf/rules/improvements.md` (or update existing rules):

```markdown
# Subagent Rules for Client Acquisition System Improvements

## Safety
- NEVER commit git changes unless explicitly asked
- NEVER modify `.env` files
- ALWAYS run tests before marking a task complete
- ALWAYS make DB schema changes backward-compatible

## Code Style
- Follow SQLAlchemy 2.0 patterns (Mapped, mapped_column)
- Use type hints everywhere
- Prefer dataclasses for new business logic
- Keep Playwright selectors in centralized `src/selectors.py`

## Testing
- Every new module needs `tests/test_{module}.py`
- Mock external APIs (Ollama, WhatsApp Web, Google Maps)
- Integration tests must use temp SQLite DBs
```

### 6.3 Continuous Improvement Pipeline

After deployment, the system should **self-improve**:

1. **Pitch Performance Tracking:** Store which pitches got replies. A/B test template versions.
2. **Auto-Prompt Evolution:** Monthly, feed top 20 performing pitches back into the prompt template as few-shot examples.
3. **Membership Idea Validation:** Track which concepts owners ask about most. Retire low-interest concepts.
4. **Error Pattern Analysis:** Aggregate vision agent failures. If 80% fail on Google Maps consent dialog, prioritize that fix.

---

## 7. Implementation Roadmap

### Sprint 1: Foundation (Week 1)
- [ ] T1.1 Create `src/ai_engine.py` with grammar constraints, validation, multi-model fallback
- [ ] T1.2 Create `src/prompts/` Jinja2 template system
- [ ] T1.3 Add `PitchCache` model
- [ ] T1.4 Refactor `researcher.py` to use new AI engine
- [ ] T1.5 Write comprehensive tests

**Deliverable:** Consistent, validated pitch generation with <5% fallback rate.

### Sprint 2: Intelligence (Week 2)
- [ ] T2.1 Enhance Maps scraper (ratings, reviews, price level)
- [ ] T2.2 Enhance website auditor (CMS detection)
- [ ] T2.3 Create `business_intelligence.py` with Maturity Matrix
- [ ] T2.4 Update prompts with maturity-aware benefits
- [ ] T2.5 Update DB models

**Deliverable:** Every lead gets a `BusinessReportCard` with maturity stage and pain points.

### Sprint 3: Value Hooks (Week 3)
- [ ] T3.1 Create `membership_ideas.py` with full concept library
- [ ] T3.2 Inject membership concepts into pitches
- [ ] T3.3 Track membership ideas in DB and dashboard
- [ ] T3.4 Validate with 5 mock pitches per business type

**Deliverable:** Pitches now include a specific membership/loyalty concept with pricing and ROI.

### Sprint 4: Automation (Week 4)
- [ ] T4.1 Follow-up sequence engine
- [ ] T4.2 Reply intent parser
- [ ] T4.3 New DB models for CRM
- [ ] T4.4 Dashboard Kanban + bulk actions
- [ ] T4.5 Batch CLI mode
- [ ] T4.6 Hot lead notifications

**Deliverable:** System can run headless overnight, auto-follow-up, and alert on hot leads.

### Sprint 5: Polish & Scale (Week 5)
- [ ] Performance optimization (parallel scraping, connection pooling)
- [ ] Multi-city batch runner
- [ ] A/B testing framework for pitches
- [ ] Export pipeline (CSV, PDF proposals)
- [ ] Mobile-responsive dashboard improvements

**Deliverable:** Production-ready system capable of 500+ leads/week with minimal manual intervention.

---

## Appendix A: Example Improved Pitch

### Business: "Café Largo", Mumbai
### Type: Café
### Years in Business: 8
### Website: None
### Rating: 4.3★ (127 reviews)
### Maturity: Established

---

**Subject:** A quick idea for Café Largo's next 8 years

Hi Café Largo team,

I've been visiting your reviews — 127 people took time to say how much they love your coffee. That's a real community you've built over 8 years in Mumbai.

Here's what caught my attention: your regulars know you, but new customers searching "café near Dadar" can't find you. You don't have a website, which means you're invisible to anyone who wasn't personally recommended — and that's a lot of morning commuters and laptop workers.

**Here's an idea:** What if you turned those regulars into members?

We could build you a **"Regulars Club"** — customers pay ₹299/month for one free coffee every day plus 10% off everything else. The website handles sign-ups, payments, and even generates a QR code they show at the counter.

With just 50 members, that's ₹14,950 in predictable monthly revenue — enough to cover most cafés' rent in this area. Plus members visit 3x more often than non-members.

The site would also show your menu, let people book tables for weekends, and collect Google reviews while they wait for their order.

Would you be open to a 15-minute call where I show you how this would look for Café Largo specifically? No commitment — just a look.

Best,
[Your name]

---

**Why this works:**
- **Specific numbers** (₹14,950, 50 members, 3x visits) create credibility
- **Membership concept** is the hook — website is the enabler, not the product
- **Maturity-aware** — 8-year café gets "next 8 years" framing, not "you need to exist online"
- **Low friction close** — "15-minute call, no commitment"

---

## Appendix B: Quick Wins (Do These Today)

1. **Lower temperature to 0.3** in `researcher.py` — immediate consistency gain
2. **Add review count and rating** to `discovery.py` extraction — 2 lines of JS
3. **Change pitch subject line** from generic to "A quick idea for [Business Name]'s next [years] years" — immediate open-rate boost
4. **Add one membership sentence** to current pitches — "We could even build you a simple loyalty program through the site" — test conversion lift
5. **Create a "Hot Leads" filter** in dashboard — show leads with "responded" status first

---

*Document Version: 1.0*
*Last Updated: 2026-05-16*
*Next Review: After Sprint 1 completion*
