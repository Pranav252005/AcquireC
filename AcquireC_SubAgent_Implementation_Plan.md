# AcquireC — Sub-Agent Driven Implementation Plan
## From 16 Leads to 20,000 Leads | Anthropic OSS Deadline: June 30, 2026

---

## Executive Summary

This plan transforms AcquireC from a single-threaded script into a **sub-agent-driven distributed architecture** where 8 autonomous agents run in parallel. Each agent owns one domain, communicates via a message bus, and can be developed/deployed independently.

**Target:** 20,000 leads/day capability | **Deadline:** 6 weeks (June 30)

---

## Part 1: Sub-Agent Architecture

```
+---------------------------------------------------------------+
|                    ORCHESTRATOR AGENT                          |
|         (FastAPI + Celery + Redis + PostgreSQL)                |
|  +-------------+  +-------------+  +---------------------+  |
|  | Task Queue  |  | Preset Mgr  |  | Connector Registry  |  |
|  | (Celery)    |  | (SQLite)    |  | (Plugin System)     |  |
|  +------+------+  +-------------+  +---------------------+  |
+--------|------------------------------------------------------+
         | Message Bus (Redis Pub/Sub + Job Queues)
    +----|----+-----------+-----------+-----------+-----------+
    |    |    |           |           |           |           |
    v    v    v           v           v           v           v
+--------+ +--------+ +----------+ +--------+ +--------+ +--------+
|Discovery| |Enrich  | |Pitch     | |Delivery| |FollowUp| |Dashboard|
|Agent xN | |Agent   | |Agent     | |Agent   | |Agent   | |Agent   |
+--------+ +--------+ +----------+ +--------+ +--------+ +--------+
    |
    v
+--------------+
| Proxy Pool   |
| (Rotating)   |
| 1000+ IPs    |
+--------------+
```

### Agent Specifications

#### Agent 1: ORCHESTRATOR
**Responsibility:** Task distribution, preset loading, result aggregation, health monitoring
**Tech:** FastAPI + Celery + Redis + PostgreSQL
**API Endpoints:**
```python
POST /api/v1/jobs              # Submit scraping job
GET  /api/v1/jobs/{id}         # Check job status
GET  /api/v1/jobs/{id}/results # Get results (paginated)
POST /api/v1/presets           # Create custom preset
GET  /api/v1/presets           # List presets
POST /api/v1/connectors/test   # Test connector config
```
**Why PostgreSQL instead of SQLite:**
- SQLite locks the entire DB on write -> crashes with 8 parallel agents
- PostgreSQL handles 20K concurrent writes, row-level locking, connection pooling
- Required for 20K leads/day

#### Agent 2: DISCOVERY AGENT (Scalable xN instances)
**Responsibility:** Scrape Google Maps, Justdial, Yelp, etc.
**Tech:** Playwright + Proxy Rotation + Celery Workers
**Parallelization Strategy:**
```python
# Instead of 1 browser scraping sequentially:
# Spawn N workers, each with their own proxy + browser context

class DiscoveryWorker:
    def __init__(self, worker_id, proxy):
        self.browser = playwright.chromium.launch(proxy=proxy)
        self.context = self.browser.new_context()

    def scrape_city(self, city, category, max_leads):
        # Each worker handles 1 city-category combo
        # Results pushed to Redis queue for Enrichment Agent
        pass

# Deploy 10 workers = 10 cities scraped in parallel
# Each worker targets 50 leads = 500 leads per batch
# 4 batches/hour = 2,000 leads/hour
# 10 hours = 20,000 leads
```

**Proxy Strategy for 20K Scale:**
```python
# Free tier: Rotating public proxy lists (scraped from free-proxy-list.net)
# Paid tier: BrightData residential proxies ($5/GB, ~$0.001/request)
# Hybrid: Free for <500/day, auto-switch to paid for >500/day

class ProxyPool:
    def __init__(self):
        self.free_proxies = self._scrape_free_lists()  # ~200 proxies
        self.paid_proxies = BrightDataProxyPool()        # Unlimited
        self.current_index = 0
        self.failure_counts = {}

    def get_next(self):
        proxy = self.pool[self.current_index % len(self.pool)]
        self.current_index += 1
        if self.failure_counts.get(proxy, 0) > 3:
            return self.get_next()  # Skip dead proxy
        return proxy

    def mark_failed(self, proxy):
        self.failure_counts[proxy] = self.failure_counts.get(proxy, 0) + 1
```

**Auto-City Switching Logic:**
```python
CITY_TIERS = {
    "tier_1_india": ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune", "Kolkata", "Ahmedabad"],
    "tier_2_india": ["Jaipur", "Lucknow", "Kanpur", "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam", "Patna", "Vadodara", "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Faridabad", "Meerut", "Rajkot", "Varanasi"],
    "tier_3_india": ["Srinagar", "Amritsar", "Allahabad", "Ranchi", "Guwahati", "Chandigarh", "Mysore", "Coimbatore", "Kochi", "Thiruvananthapuram", "Mangalore", "Hubli", "Belgaum", "Dehradun", "Gwalior", "Raipur", "Jabalpur", "Jodhpur"],
    "tier_1_global": ["New York", "London", "Singapore", "Dubai", "Sydney", "Toronto"],
}

class CityRotator:
    def __init__(self, target_count, preset):
        self.target = target_count
        self.found = 0
        self.city_queue = self._build_queue(preset)
        self.exhausted_cities = set()

    def _build_queue(self, preset):
        # Order: tier_1 -> tier_2 -> tier_3 -> global
        cities = []
        for tier in ["tier_1_india", "tier_2_india", "tier_3_india", "tier_1_global"]:
            cities.extend(CITY_TIERS.get(tier, []))
        return cities

    def get_next_city(self):
        for city in self.city_queue:
            if city not in self.exhausted_cities:
                return city
        return None  # All cities exhausted

    def mark_exhausted(self, city, found_count):
        if found_count < 5:  # City is tapped out
            self.exhausted_cities.add(city)
        self.found += found_count
```

#### Agent 3: ENRICHMENT AGENT
**Responsibility:** Website audit, email extraction, business intelligence scoring
**Tech:** Playwright (lightweight) + requests + BeautifulSoup + Celery
**Parallelization:**
```python
# For 20K leads, website audits are the bottleneck
# Solution: Two-tier approach

class EnrichmentWorker:
    def process_lead(self, lead):
        # Tier 1: Fast HTTP audit (2 seconds)
        result = self._http_audit(lead.website)

        # Tier 2: Full Playwright audit only if website exists and looks complex
        if result["has_website"] and result["cms"] is None:
            result = self._playwright_audit(lead.website)

        # Email extraction (parallel HTTP requests)
        emails = self._extract_emails(lead.website)

        # Business intelligence scoring
        score = LeadScorer.score(...)
        maturity = MaturityAnalyzer.analyze(...)

        return EnrichedLead(lead, result, emails, score, maturity)

# Deploy 20 enrichment workers
# Each processes 1 lead every 5 seconds
# 20 workers x 12 leads/min = 240 leads/min = 14,400 leads/hour
```

**Email Extraction at Scale:**
```python
import aiohttp
import asyncio
import re

class EmailExtractor:
    def __init__(self):
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=100)  # 100 concurrent connections
        )

    async def extract(self, website):
        if not website:
            return None

        paths = ["", "/contact", "/about", "/contact-us", "/reach-us", "/about-us"]
        tasks = [self._fetch(website + path) for path in paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for html in results:
            if isinstance(html, str):
                emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
                for e in emails:
                    if self._is_valid(e):
                        return e
        return None

    def _is_valid(self, email):
        invalid = ["example.com", "domain.com", "yourdomain", "test@", "admin@localhost"]
        return not any(x in email.lower() for x in invalid)
```

#### Agent 4: PITCH AGENT
**Responsibility:** AI-powered pitch generation via BYOK connectors
**Tech:** llama.cpp (local) + OpenAI API + Anthropic API + Ollama
**Connector Architecture:**
```python
from abc import ABC, abstractmethod

class LLMConnector(ABC):
    @abstractmethod
    def generate_pitch(self, context: BusinessContext, preset: Preset) -> PitchResult:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

class LocalConnector(LLMConnector):
    # Your 9B Q4KM via llama-cpp-python
    def __init__(self, model_path):
        self.llm = Llama(model_path=model_path, n_ctx=4096)

    def generate_pitch(self, context, preset):
        prompt = self._build_prompt(context, preset)
        output = self.llm.create_completion(
            prompt=prompt,
            max_tokens=1024,
            temperature=0.7,
            grammar=PITCH_GRAMMAR  # GBNF constraint
        )
        return self._parse_output(output)

class OpenAIConnector(LLMConnector):
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def generate_pitch(self, context, preset):
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": preset.system_prompt},
                {"role": "user", "content": self._build_prompt(context, preset)}
            ],
            response_format={"type": "json_object"}
        )
        return self._parse_output(response.choices[0].message.content)

class AnthropicConnector(LLMConnector):
    def __init__(self, api_key):
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_pitch(self, context, preset):
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            system=preset.system_prompt,
            messages=[{"role": "user", "content": self._build_prompt(context, preset)}]
        )
        return self._parse_output(response.content[0].text)

class OllamaConnector(LLMConnector):
    def __init__(self, model="qwen3.5:9b"):
        self.model = model

    def generate_pitch(self, context, preset):
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": self.model,
            "prompt": self._build_prompt(context, preset),
            "format": "json",
            "stream": False
        })
        return self._parse_output(response.json()["response"])

# Registry
CONNECTORS = {
    "local": LocalConnector,
    "openai": OpenAIConnector,
    "anthropic": AnthropicConnector,
    "ollama": OllamaConnector,
    "openrouter": OpenRouterConnector,
}
```

**Pitch Caching (Fixed):**
```python
class PitchCacheManager:
    @staticmethod
    def _hash_context(ctx: BusinessContext, preset_id: str) -> str:
        key_data = {
            "preset": preset_id,
            "type": ctx.business_type,
            "stage": ctx.maturity_stage,
            "score": ctx.website_score,
            "years": ctx.years_in_business,
            "city": ctx.city,           # FIXED: Added
            "name": ctx.name,           # FIXED: Added
            "has_website": ctx.has_website,
            "issues": ctx.website_issues,
        }
        raw = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()
```

#### Agent 5: DELIVERY AGENT
**Responsibility:** Draft generation, CRM export, report compilation
**Tech:** Jinja2 + ReportLab + CSV/Excel generation + CRM APIs
**CRM Connectors:**
```python
class CRMConnector(ABC):
    @abstractmethod
    def export_leads(self, leads: List[Lead]):
        pass

class NotionConnector(CRMConnector):
    def __init__(self, token, database_id):
        self.client = Client(auth=token)
        self.db = database_id

    def export_leads(self, leads):
        for lead in leads:
            self.client.pages.create(
                parent={"database_id": self.db},
                properties={
                    "Name": {"title": [{"text": {"content": lead.business_name}}]},
                    "City": {"rich_text": [{"text": {"content": lead.city}}]},
                    "Score": {"number": lead.score},
                    "Status": {"select": {"name": lead.status}},
                }
            )

class AirtableConnector(CRMConnector):
    def __init__(self, api_key, base_id, table_name):
        self.table = Table(api_key, base_id, table_name)

    def export_leads(self, leads):
        records = [{"fields": lead.to_dict()} for lead in leads]
        self.table.batch_create(records)

class GoogleSheetsConnector(CRMConnector):
    def __init__(self, creds_path, spreadsheet_id):
        self.sheet = gspread.service_account(filename=creds_path)
        self.worksheet = self.sheet.open_by_key(spreadsheet_id).sheet1

    def export_leads(self, leads):
        rows = [lead.to_row() for lead in leads]
        self.worksheet.append_rows(rows)

class HubSpotConnector(CRMConnector):
    def __init__(self, api_key):
        self.client = HubSpot(api_key=api_key)

    def export_leads(self, leads):
        for lead in leads:
            self.client.crm.contacts.basic_api.create(
                simple_public_object_input=SimplePublicObjectInput(
                    properties={
                        "email": lead.email,
                        "firstname": lead.business_name,
                        "city": lead.city,
                        "phone": lead.phone,
                    }
                )
            )
```

**Report Generation:**
```python
class ReportAgent:
    def generate_daily_report(self, date, leads):
        # PDF with charts
        # CSVs: by-city, by-category, by-contact-type, by-score
        # Excel with multiple sheets
        pass
```

#### Agent 6: FOLLOW-UP AGENT
**Responsibility:** Schedule and generate follow-up sequences
**Tech:** Celery Beat (cron) + PostgreSQL
**Auto-Schedule:**
```python
class FollowUpScheduler:
    SEQUENCES = {
        "gentle": [3, 7, 14, 30],
        "aggressive": [2, 4, 7, 14, 30],
        "b2b_enterprise": [7, 14, 30, 60, 90],
    }

    def schedule(self, lead, preset):
        sequence = preset.follow_up_sequence or "gentle"
        for day in self.SEQUENCES[sequence]:
            scheduled = datetime.now(timezone.utc) + timedelta(days=day)
            FollowUp.create(
                lead_id=lead.id,
                scheduled_at=scheduled,
                channel="email",  # or whatsapp, linkedin
                tone=self._get_tone(day),
            )

        # Celery Beat task runs every hour to process due follow-ups
        # Generates draft, marks as SENT, notifies user
```

#### Agent 7: DASHBOARD AGENT
**Responsibility:** Real-time monitoring, Kanban board, analytics
**Tech:** FastAPI + Jinja2 + Chart.js + WebSocket
**Real-time Updates:**
```python
# WebSocket for live job progress
@app.websocket("/ws/jobs/{job_id}")
async def job_websocket(websocket: WebSocket, job_id: str):
    await websocket.accept()
    while True:
        progress = await redis.get(f"job:{job_id}:progress")
        await websocket.send_json(json.loads(progress))
        await asyncio.sleep(2)
```

**Performance Optimizations:**
```python
# Fix N+1 query
@app.get("/")
def index(db: Session = Depends(get_db)):
    # OLD: for lead in db.query(Lead).all(): ...
    # NEW: Single aggregation query
    stats = db.query(
        func.count(Lead.id).label("total"),
        func.count(case((Lead.status == "contacted", 1))).label("contacted"),
        func.count(case((Lead.status == "responded", 1))).label("responded"),
        func.count(case((Lead.status == "failed", 1))).label("failed"),
    ).first()

    hot = db.query(Lead).filter(Lead.score >= 70).order_by(Lead.score.desc()).limit(50).all()

    return templates.TemplateResponse("index.html", {
        "stats": stats,
        "hot_leads": hot,
    })
```

#### Agent 8: PRESET AGENT
**Responsibility:** Preset marketplace, validation, community submissions
**Tech:** JSON Schema validation + GitHub API + SQLite
**Preset Structure:**
```json
{
  "id": "web_design_agency_v1",
  "name": "Web Design Agency",
  "version": "1.0.0",
  "author": "acquirec-team",
  "description": "Find local businesses that need modern websites",
  "target": {
    "categories": ["cafe", "restaurant", "salon", "clinic", "gym", "retail"],
    "cities": ["auto_rotate"],
    "countries": ["IN", "US", "UK", "AU"]
  },
  "scrapers": ["google_maps", "justdial", "yelp"],
  "pain_points": {
    "detectors": [
      {"id": "no_website", "weight": 1.0},
      {"id": "not_mobile_friendly", "weight": 0.8},
      {"id": "slow_load", "weight": 0.6},
      {"id": "no_online_booking", "weight": 0.9}
    ]
  },
  "pitch": {
    "tone": "friendly_professional",
    "max_length": 1200,
    "must_include": ["website", "digital presence", "customers"]
  },
  "membership": {
    "concepts": {
      "cafe": "Coffee Club",
      "salon": "Style Pass",
      "clinic": "Care Plan"
    }
  },
  "follow_up": {
    "sequence": "gentle",
    "channels": ["email"]
  },
  "system_prompt": "You are a web design consultant..."
}
```

**Community Preset Submission:**
```python
class PresetMarketplace:
    def submit_preset(self, preset_json, author):
        # Validate against JSON Schema
        # Run test generation on 5 sample businesses
        # If tests pass, create PR to github.com/Pranav252005/AcquireC-presets
        # Auto-merge if CI passes
        pass
```

---

## Part 2: Scalability Architecture for 20,000 Leads

### The Math

| Metric | Current | Target | Required Change |
|--------|---------|--------|-----------------|
| Leads/batch | 16 | 20,000 | 1,250x |
| Time/batch | 10 min | 2 hours | 8x faster per lead |
| Browser instances | 1 | 10 | Parallelize |
| Database | SQLite | PostgreSQL | Concurrent writes |
| Proxy usage | None | 1,000+ IPs | Avoid blocks |

### Architecture for 20K

```
+---------------------------------------------------------------+
|                     JOB SUBMISSION                             |
|  User: "I need 20,000 leads for web_design in India"          |
+---------------------|-----------------------------------------+
                      v
+---------------------------------------------------------------+
|              ORCHESTRATOR: Job Decomposition                  |
|  1. Split into city-category chunks (50 leads each)          |
|  2. Create 400 tasks: 20 cities x 20 categories              |
|  3. Push to Redis task queue                                  |
+---------------------|-----------------------------------------+
                      v
+---------------------------------------------------------------+
|              CELERY WORKER POOL (10 workers)                   |
|  Worker 1-5:  Discovery (Google Maps + Justdial)             |
|  Worker 6-8:  Enrichment (Website audit + Email extract)     |
|  Worker 9:   Pitch Generation (Local LLM / BYOK)            |
|  Worker 10:  Delivery (CRM export + Report generation)         |
|                                                               |
|  Each worker: 1 Playwright context + rotating proxy           |
+---------------------|-----------------------------------------+
                      v
+---------------------------------------------------------------+
|              RESULT AGGREGATION + DEDUPLICATION                |
|  - PostgreSQL with UNIQUE(city, business_name)               |
|  - Redis Bloom filter for fast duplicate check               |
|  - Stream results to dashboard via WebSocket                 |
+---------------------------------------------------------------+
```

### Rate Limiting & Politeness

```python
class RateLimiter:
    # Respect Google Maps and avoid bans

    def __init__(self):
        self.last_request = {}
        self.min_delay = 2.0  # seconds between requests per proxy
        self.daily_limit = 500  # requests per proxy per day

    async def wait(self, proxy_id):
        now = time.time()
        last = self.last_request.get(proxy_id, 0)
        elapsed = now - last
        if elapsed < self.min_delay:
            await asyncio.sleep(self.min_delay - elapsed)
        self.last_request[proxy_id] = time.time()

    def can_use(self, proxy_id):
        today_count = redis.get(f"proxy:{proxy_id}:count:{date.today()}") or 0
        return int(today_count) < self.daily_limit
```

### Database Schema (PostgreSQL)

```sql
-- Main leads table with partitioning for 20K+ rows
CREATE TABLE leads (
    id BIGSERIAL PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    business_name VARCHAR(255) NOT NULL,
    business_type VARCHAR(50) NOT NULL,
    address TEXT,
    phone VARCHAR(50),
    email VARCHAR(255),
    website VARCHAR(500),
    rating DECIMAL(2,1),
    review_count INTEGER,
    has_website BOOLEAN DEFAULT FALSE,
    website_score VARCHAR(20),
    maturity_stage VARCHAR(20),
    digital_readiness INTEGER,
    score INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'new',
    preset_id VARCHAR(100),
    job_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(city, business_name)
);

-- Partition by month for performance
CREATE TABLE leads_2026_05 PARTITION OF leads
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

-- Index for fast queries
CREATE INDEX idx_leads_city ON leads(city);
CREATE INDEX idx_leads_score ON leads(score DESC);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_job ON leads(job_id);

-- Outreach table
CREATE TABLE outreach (
    id BIGSERIAL PRIMARY KEY,
    lead_id BIGINT REFERENCES leads(id),
    channel VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    content TEXT,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Follow-ups table
CREATE TABLE follow_ups (
    id BIGSERIAL PRIMARY KEY,
    lead_id BIGINT REFERENCES leads(id),
    scheduled_at TIMESTAMP NOT NULL,
    channel VARCHAR(20),
    tone VARCHAR(20),
    status VARCHAR(20) DEFAULT 'pending',
    content TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Jobs table for tracking batch operations
CREATE TABLE jobs (
    id VARCHAR(100) PRIMARY KEY,
    preset_id VARCHAR(100) NOT NULL,
    target_count INTEGER NOT NULL,
    found_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running',
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    config JSONB
);
```

---

## Part 3: Implementation Timeline (6 Weeks to Anthropic Deadline)

### Week 1: Foundation (Days 1-7)
**Parallel Tracks:**

**Track A: Infrastructure (Days 1-3)**
- [ ] Replace SQLite with PostgreSQL
- [ ] Add Redis for task queue + caching
- [ ] Add Celery + Celery Beat
- [ ] Docker Compose setup (PostgreSQL + Redis + App)
- [ ] Environment-based config (dev/staging/prod)

**Track B: Bug Fixes (Days 1-3)**
- [ ] Fix PitchCacheManager hash (add city + name)
- [ ] Implement real email extraction
- [ ] Fix MembershipLibrary duplicates (spa, doctor, fitness)
- [ ] Fix WebsiteAuditor boundary (>= 8000)
- [ ] Fix discovery dedup (city + name)
- [ ] Fix dashboard N+1 query
- [ ] Remove auto-WhatsApp (keep drafts)
- [ ] Fix vision mapper DOM mutation

**Track C: Connectors (Days 4-7)**
- [ ] LLM Connector base class + Local connector
- [ ] OpenAI connector
- [ ] Anthropic connector
- [ ] Ollama connector
- [ ] Connector registry + config UI

**Track D: Preset System (Days 4-7)**
- [ ] Preset JSON Schema
- [ ] Preset loader + validator
- [ ] 5 default presets (web_design, seo, social_media, real_estate, insurance)
- [ ] Preset CLI commands

**Deliverable:** Working system with BYOK + presets + PostgreSQL

### Week 2: Scalability (Days 8-14)
**Parallel Tracks:**

**Track A: Discovery Scaling (Days 8-10)**
- [ ] Proxy pool implementation (free + paid)
- [ ] Auto-city switching logic
- [ ] Multi-worker discovery (5 parallel workers)
- [ ] Justdial scraper connector
- [ ] Job queue + progress tracking

**Track B: Enrichment Scaling (Days 8-10)**
- [ ] Async HTTP audit (aiohttp)
- [ ] Parallel email extraction
- [ ] Batch business intelligence scoring
- [ ] Redis Bloom filter for dedup

**Track C: Delivery Scaling (Days 11-14)**
- [ ] Notion connector
- [ ] Airtable connector
- [ ] Google Sheets connector
- [ ] HubSpot connector (optional)
- [ ] Batch report generation (PDF + Excel + CSV)

**Track D: Dashboard v2 (Days 11-14)**
- [ ] WebSocket live progress
- [ ] Job management UI (start/stop/pause)
- [ ] Real-time analytics (Chart.js)
- [ ] Lead filtering + search

**Deliverable:** Can process 1,000 leads in <30 minutes

### Week 3: Polish + Launch Prep (Days 15-21)
**Track A: README + Docs (Days 15-17)**
- [ ] Killer README with GIF demo
- [ ] One-command install instructions
- [ ] Comparison table vs competitors
- [ ] Architecture diagram
- [ ] Contributing guide

**Track B: Testing (Days 15-17)**
- [ ] Unit tests for all agents (pytest)
- [ ] Integration tests for full pipeline
- [ ] Load test: 1,000 leads

**Track C: Multi-Country (Days 18-21)**
- [ ] Yelp scraper (US/UK/AU)
- [ ] Yellow Pages scraper
- [ ] TripAdvisor scraper (hotels/restaurants)
- [ ] Country-aware preset configs

**Track D: SaaS Prep (Days 18-21)**
- [ ] Docker image for cloud deploy
- [ ] Environment-based feature flags
- [ ] Admin dashboard
- [ ] User authentication (optional)

**Deliverable:** Production-ready, launchable

### Week 4: LAUNCH WEEK (Days 22-28)
**Day 22:** Hacker News "Show HN" post
**Day 23:** Product Hunt launch
**Day 24:** Reddit posts (r/selfhosted, r/Python, r/coldemail, r/LeadGeneration)
**Day 25:** Dev.to + Hashnode articles
**Day 26:** Console.dev submission
**Day 27:** YouTube demo video
**Day 28:** Monitor, respond to issues, fix critical bugs

**Target:** 1,000-2,000 GitHub stars

### Week 5: Community + Features (Days 29-35)
**Track A: Community (Days 29-31)**
- [ ] Discord server setup
- [ ] Preset marketplace (GitHub repo + PR workflow)
- [ ] Community preset submissions (target: 10 user presets)
- [ ] Issue triage + PR reviews

**Track B: Advanced Features (Days 32-35)**
- [ ] LinkedIn enrichment (via Proxycurl API - optional)
- [ ] Instagram DM draft generation
- [ ] AI-powered lead scoring v2 (ML model)
- [ ] Export to Mailchimp/SendGrid

**Track C: Marketing (Days 32-35)**
- [ ] Blog: "How I built a 20K lead engine on a 4GB laptop"
- [ ] Blog: "Privacy-first lead generation with local LLMs"
- [ ] Newsletter features (TLDR, Console.dev)

**Target:** 2,500-3,500 stars

### Week 6: Final Push + Anthropic Application (Days 36-42)
**Track A: SaaS Launch (Days 36-38)**
- [ ] Hosted version (free tier: 50 leads/month)
- [ ] Paid tier: $19/month unlimited
- [ ] Stripe integration
- [ ] Landing page

**Track B: Enterprise (Days 39-40)**
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Webhook support
- [ ] Team collaboration features
- [ ] White-label option

**Track C: Anthropic Application (Days 41-42)**
- [ ] Prepare ecosystem impact narrative
- [ ] Document downstream usage (presets, connectors, Docker deploys)
- [ ] Apply via exception track
- [ ] Follow up with Anthropic team

**Target:** 4,000-5,500 stars + Anthropic acceptance

---

## Part 4: Docker Deployment (One-Command Setup)

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: acquirec
      POSTGRES_USER: acquirec
      POSTGRES_PASSWORD: ${DB_PASSWORD:-acquirec123}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  acquirec:
    build: .
    environment:
      - DATABASE_URL=postgresql://acquirec:${DB_PASSWORD:-acquirec123}@postgres:5432/acquirec
      - REDIS_URL=redis://redis:6379
      - LLM_PROVIDER=${LLM_PROVIDER:-local}
      - LOCAL_MODEL_PATH=${LOCAL_MODEL_PATH}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./data:/app/data
      - ./models:/app/models
      - ./presets:/app/presets
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    command: >
      sh -c "alembic upgrade head && 
             celery -A acquirec.celery worker --loglevel=info --concurrency=10 &
             celery -A acquirec.celery beat --loglevel=info &
             uvicorn acquirec.main:app --host 0.0.0.0 --port 8000"

  dashboard:
    build: .
    environment:
      - DATABASE_URL=postgresql://acquirec:${DB_PASSWORD:-acquirec123}@postgres:5432/acquirec
    ports:
      - "8001:8001"
    command: uvicorn acquirec.dashboard:app --host 0.0.0.0 --port 8001

volumes:
  postgres_data:
```

**One-Command Install:**
```bash
git clone https://github.com/Pranav252005/AcquireC.git
cd AcquireC
cp .env.example .env
# Edit .env with your API keys (optional)
docker-compose up -d
# Access dashboard at http://localhost:8001
```

---

## Part 5: The Honest Reality of 20,000 Leads

### What 20K Actually Means

| Scenario | Reality |
|----------|---------|
| **20K leads from 1 city** | Impossible. Mumbai has ~2,000 cafes total. |
| **20K leads from India** | Possible. 50 cities x 20 categories x 20 leads = 20,000 |
| **20K leads in 1 hour** | Impossible without 100+ proxies and workers |
| **20K leads in 1 day** | Possible with 10 workers + paid proxies |
| **20K leads with free proxies** | Will take 3-5 days (rate limited by Google) |
| **20K leads with paid proxies** | 8-12 hours (BrightData residential) |

### The Cost of 20K Leads

| Resource | Free Tier | Paid Tier (for 20K) |
|----------|-----------|---------------------|
| Proxies | Public lists (200 IPs, slow) | BrightData: ~$5-10/day |
| LLM | Local 9B (free, slow) | OpenAI: ~$5-10 for 20K pitches |
| Database | SQLite (crashes) | PostgreSQL (free, self-hosted) |
| Workers | 1 laptop | 1 laptop + cloud workers |
| CRM Export | Local files | Notion/Airtable APIs (free tiers) |

**Bottom line:** 20K leads/day costs ~$10-20 in proxies + API credits. Without paid proxies, expect 3-5K leads/day max.

---

## Part 6: File Structure (Post-Refactor)

```
AcquireC/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
├── alembic/                    # Database migrations
├── presets/
│   ├── web_design_agency.json
│   ├── seo_freelancer.json
│   ├── social_media_manager.json
│   ├── real_estate_agent.json
│   ├── insurance_agent.json
│   └── README.md
├── src/
│   ├── __init__.py
│   ├── main.py                 # Orchestrator + API
│   ├── config.py               # Pydantic settings
│   ├── database.py             # PostgreSQL + models
│   ├── celery_app.py           # Celery configuration
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # Job management
│   │   ├── discovery.py         # Google Maps + Justdial + Yelp
│   │   ├── enrichment.py      # Website audit + email extract
│   │   ├── pitch.py             # LLM connector + pitch generation
│   │   ├── delivery.py          # CRM export + reports
│   │   ├── follow_up.py         # Scheduled sequences
│   │   └── dashboard.py         # FastAPI + WebSocket
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── llm/
│   │   │   ├── base.py
│   │   │   ├── local.py
│   │   │   ├── openai.py
│   │   │   ├── anthropic.py
│   │   │   ├── ollama.py
│   │   │   └── openrouter.py
│   │   ├── scrapers/
│   │   │   ├── base.py
│   │   │   ├── google_maps.py
│   │   │   ├── justdial.py
│   │   │   ├── yelp.py
│   │   │   └── yellow_pages.py
│   │   ├── crm/
│   │   │   ├── base.py
│   │   │   ├── notion.py
│   │   │   ├── airtable.py
│   │   │   ├── google_sheets.py
│   │   │   └── hubspot.py
│   │   └── messenger/
│   │       ├── base.py
│   │       ├── email_drafts.py
│   │       └── whatsapp_drafts.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── proxy_pool.py        # Proxy rotation
│   │   ├── rate_limiter.py      # Politeness controls
│   │   └── dedup.py             # Bloom filter dedup
│   ├── presets/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   ├── validator.py
│   │   └── marketplace.py
│   ├── business_intelligence/
│   │   ├── __init__.py
│   │   ├── maturity.py
│   │   ├── scoring.py
│   │   └── membership.py
│   └── utils/
│       ├── __init__.py
│       ├── email_extractor.py
│       ├── report_generator.py
│       └── validators.py
├── tests/
│   ├── __init__.py
│   ├── test_discovery.py
│   ├── test_enrichment.py
│   ├── test_pitch.py
│   ├── test_connectors.py
│   └── test_presets.py
├── data/                        # SQLite fallback (dev only)
├── reports/                     # Generated reports
├── models/                      # Local LLM models
└── docs/
    ├── architecture.md
    ├── connectors.md
    └── presets.md
```

---

## Summary: What to Build This Week

If you want to hit the Anthropic deadline, here's your **Week 1 minimum viable refactor:**

1. **Monday:** PostgreSQL + Redis + Celery setup
2. **Tuesday:** Fix all 8 bugs + add LLM connectors (local + OpenAI + Anthropic)
3. **Wednesday:** Preset system (5 presets) + auto-city switching
4. **Thursday:** Proxy pool + multi-worker discovery
5. **Friday:** Dashboard v2 + WebSocket progress
6. **Saturday:** Docker Compose + README rewrite
7. **Sunday:** Test everything, fix critical issues

**Monday Week 2:** Launch on HN + PH + Reddit simultaneously.

The clock is ticking. Build the sub-agent architecture. Ship this week.
