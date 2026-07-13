# Ideas Lab & Content Calendar — Full Architecture Guide

> Complete technical reference for replicating these features in another dashboard.
> Based on the Right Horizons Reporting codebase (FastAPI + vanilla JS).

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Tech Stack](#2-tech-stack)
3. [Content Calendar](#3-content-calendar)
4. [Ideas Lab](#4-ideas-lab)
5. [AI Module (`ai.py`)](#5-ai-module-aipy)
6. [Live Context Enrichment](#6-live-context-enrichment)
7. [Data Storage & Persistence](#7-data-storage--persistence)
8. [Repetition Avoidance System](#8-repetition-avoidance-system)
9. [Frontend Architecture](#9-frontend-architecture)
10. [Domain Filtering](#10-domain-filtering)
11. [Replication Checklist](#11-replication-checklist)

---

## 1. High-Level Architecture

```
┌──────────────────────────────────────────────────────────┐
│  BROWSER (static/index.html + static/app.js)             │
│  ┌─────────────────┐  ┌─────────────────────────────┐    │
│  │ Content Calendar │  │ Ideas Lab                   │    │
│  │ Tab              │  │ (5 sub-tabs)                │    │
│  └────────┬────────┘  └─────────────┬───────────────┘    │
└───────────┼─────────────────────────┼────────────────────┘
            │  fetch()                │  fetch()
            ▼                         ▼
┌──────────────────────────────────────────────────────────┐
│  FastAPI Backend (main.py)                                │
│                                                          │
│  Calendar endpoints:           Ideas Lab endpoints:      │
│  POST /api/calendar/generate   GET  /api/ideas/lab/generate   │
│  GET  /api/calendar/get        POST /api/ideas/lab/webinar    │
│  POST /api/calendar/save       POST /api/ideas/lab/seo        │
│  GET  /api/calendar/export.csv POST /api/ideas/lab/expand     │
│  POST /api/calendar/upload     GET  /api/ideas/lab/seasonal   │
│                                GET  /api/ideas/generate       │
│                                GET  /api/ideas/notifications  │
│                                POST /api/ideas/seen           │
└──────────┬──────────────────────────┬────────────────────┘
           │                          │
           ▼                          ▼
┌─────────────────────────────────────────────────────────┐
│  ai.py → OpenRouter API (Claude Sonnet 4)               │
│  web_search.py → Tavily Search API                      │
│  google_trends.py → pytrends (Google Trends)            │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | **FastAPI** (Python) | API routes, request validation |
| AI | **OpenRouter** → Claude Sonnet 4 (fallback: Claude Haiku 4) | Content generation, JSON responses |
| Web Search | **Tavily API** | Live market context, finance news, trending content |
| Trends | **pytrends** (Google Trends) | Trending searches in India, related queries |
| Frontend | **Vanilla JS** + CSS | No framework, single `app.js` + `index.html` |
| Storage | **In-memory dicts** (server-side) + **localStorage** (client-side) | Calendar items, ideas history, saved library |
| Export | **CSV** via Python `csv` module | Calendar export |
| File Parsing | **openpyxl** (Excel), **pypdf** (PDF), **python-docx** (DOCX) | Calendar upload |

---

## 3. Content Calendar

### 3.1 Overview

The Content Calendar generates a full month of social media posts for a selected domain. Each post includes date, day, post type (Carousel/Static/Reel/Poll), swimlane (content pillar), slide-by-slide caption, description, hashtags, design notes, and references. Posts follow a Mon/Wed/Fri cadence with Case Study and Leadership Quote placeholders.

### 3.2 Backend Endpoints

#### `POST /api/calendar/generate`

**Purpose:** AI-generates a full month's social media calendar.

**Request body** (JSON, Pydantic `CalendarRequest`):
```python
class CalendarRequest(BaseModel):
    domain: str = "rh"       # Domain key: "rh", "pms", "aif", "akeana"
    month: str = ""          # Format: "YYYY-MM" (e.g., "2026-07")
    context: str = ""        # Optional additional context
```

**Processing pipeline:**
1. Looks up domain label from `DOMAINS` config dict
2. Increments `_generation_level[domain]` (tracks how many times generated — controls topic depth)
3. Builds system prompt from `CAL_SYSTEM` constant (contains "Content DNA" — brand voice, pillar distribution, post types, tone rules)
4. Builds user prompt with:
   - Generation level + level-up rules (levels 1-3 = foundational, 4-7 = intermediate, 8+ = advanced)
   - Random "variety seed": 6 random narrative devices, 4 random personas, 4 random angles (from hardcoded pools)
   - History of past posts (to avoid repetition)
   - Live web search context (Tavily: market context + finance news)
   - Google Trends context
5. Calls `ai_mod.chat_json(sys_prompt, user, max_tokens=12000, temperature=0.75)`
6. Unwraps response (handles `{items: [...]}` or raw array)
7. Stores in `_calendars[f"{domain}:{month}"]`
8. Pushes to `_calendar_history[domain]` for repetition avoidance

**Response:**
```json
{
    "items": [
        {
            "date": "2026-07-01",
            "day": "Wednesday",
            "approval_status": "",
            "type": "Carousel",
            "swimlane": "Retirement Planning",
            "caption": "Slide 1: At 55, the plan that worked at 40 starts to quietly fail...",
            "design_notes": "Navy/indigo palette, bold stat callout boxes...",
            "description": "A salaried professional turning 55 often discovers...",
            "hashtags": "#RightHorizons #RetirementPlanning #WealthManagement ...",
            "references": "",
            "platforms": ["instagram", "facebook", "linkedin"]
        }
        // ... 18-22 items per month
    ],
    "month": "2026-07",
    "domain": "rh",
    "level": 3
}
```

#### `GET /api/calendar/get`

**Purpose:** Retrieve a previously generated/uploaded calendar.

**Query params:** `domain` (default "rh"), `month` (YYYY-MM)

**Response:** `{"items": [...], "domain": "rh", "month": "2026-07"}`

#### `POST /api/calendar/save`

**Purpose:** Save inline edits made in the browser table back to the server.

**Request body:**
```json
{
    "domain": "rh",
    "month": "2026-07",
    "items": [/* ... edited items ... */]
}
```

**Response:** `{"ok": true}`

#### `GET /api/calendar/export.csv`

**Purpose:** Download the calendar as a CSV file.

**Query params:** `domain`, `month`

**CSV columns:** DATE, DAY, Approval Status, POST TYPE, Aligned Swimlane, CAPTION/Image Copy, Design Notes, DESCRIPTION, HASHTAGS, REFERENCES, IMAGE, CLIENT FEEDBACK

**Response:** CSV file download with filename `RH_SM_Calendar_{Label}_{month}.csv`

#### `POST /api/calendar/upload`

**Purpose:** Upload an existing calendar (Excel, PDF, DOCX, or text).

**Request:** `multipart/form-data` with `file`, plus query params `domain` and `month`

**Processing:**
- **Excel (.xlsx/.xls):** Parsed directly with `openpyxl` — no AI needed. Columns matched by header name (fuzzy matching). Structured data extracted into the standard item format.
- **PDF (.pdf):** Text extracted with `pypdf`, then sent to AI to generate a structured calendar from the document content.
- **DOCX (.docx):** Text extracted with `python-docx`, then sent to AI.
- **Text (.txt):** Read as UTF-8, then sent to AI.

**Response:** `{"items": [...], "month": "...", "domain": "...", "source": "excel" | "ai"}`

### 3.3 Content DNA (System Prompt)

The `RH_CONTENT_DNA` constant (~70 lines) encodes the brand's actual content strategy. This is the most important piece to customize for your dashboard. It defines:

- **Four content pillars** ("swimlanes") with percentage distribution: Retirement Planning (35%), NRI Wealth (27%), ESOPs (15%), Family Office (12%)
- **Post types** with frequency: Carousel (42%), Static Image (38%), Reel (10%), Poll (10%)
- **Voice & tone rules**: advisory not promotional, data-driven with ₹ amounts, calm/mature, no hype
- **Caption structure patterns**: slide-by-slide for carousels, bullet points for static, scene directions for reels
- **Hashtag pattern**: 12-15 tags, mandatory brand tags + swimlane tags
- **Disclaimers**: SEBI compliance requirements

The `CAL_SYSTEM` prompt wraps this DNA with calendar-specific structure rules (Mon/Wed/Fri posting cadence, 18-22 items per month, placeholder rows for Case Studies and Leadership Quotes).

### 3.4 Variety Seed System

Each generation randomly samples from three pools to ensure diversity:

```python
_devices = ["case study", "myth-buster", "regulatory deep-dive", "mistake post-mortem",
            "age-bracket walkthrough", "before/after math", "persona-driven scenario",
            "contrarian take", "framework introduction", "FAQ format", "checklist",
            "decision tree", "data-led explainer", "what-if scenario"]

_personas = ["Bangalore CTO with vested ESOPs", "Dubai-based cardiologist returning to India",
             "Mumbai founder post-exit", ...]

_angles = ["sequence-of-returns risk", "currency mismatch", "regulatory just-changed",
           "concentration risk", "tax timing", ...]
```

6 devices, 4 personas, and 4 angles are randomly selected per generation and injected into the prompt.

### 3.5 Frontend — Calendar UI

**Location:** `static/index.html` (line ~577) + `static/app.js` (line ~1894)

**HTML structure:**
```
div#view-calendar
├── toolbar
│   ├── input[type=month]#cal-month          (month picker)
│   ├── button "⚡ Generate with AI"         (calls generateCalendar())
│   ├── button "⬇ Download CSV"#cal-csv-btn  (calls downloadCalendarCSV())
│   ├── button "📄 Upload" + input#cal-file  (calls uploadCalendar())
│   └── input#cal-context                     (optional context notes)
└── div.table-card#cal-table                  (rendered table goes here)
```

**Key JS functions:**

| Function | Purpose |
|----------|---------|
| `generateCalendar()` | POSTs to `/api/calendar/generate`, renders result |
| `uploadCalendar()` | POSTs file to `/api/calendar/upload` via FormData |
| `renderCalendarTable(items)` | Builds an editable `<table>` with `contenteditable` cells |
| `downloadCalendarCSV()` | Saves edits first, then triggers CSV download |

**Inline editing:** Every table cell has `contenteditable="true"` with a `data-k` attribute mapping to the item field. On `blur`, the edited value is written back to `calendarItems[idx][field]`. Before CSV export, the current state is POSTed to `/api/calendar/save`.

---

## 4. Ideas Lab

### 4.1 Overview

The Ideas Lab is a multi-tab content ideation engine with five sub-sections:
1. **Generate Ideas** — AI-powered idea card generation with configurable brief
2. **Saved Library** — localStorage-persisted collection of saved ideas
3. **Seasonal Ideas** — Time-sensitive content opportunities based on Indian calendar
4. **Webinar Repurposing** — Convert webinar content into 15-18 content pieces
5. **SEO Ideas** — SEO-driven content plans from target keywords

### 4.2 Backend Endpoints

#### `GET /api/ideas/lab/generate`

**Purpose:** Generate 8 production-ready content idea cards.

**Query params:**
| Param | Default | Description |
|-------|---------|-------------|
| `domain` | "rh" | Domain key |
| `topic` | "" | Core topic (e.g., "NRI retirement planning") |
| `audience` | "" | Target audience (e.g., "Middle East NRIs earning ₹30L+") |
| `content_type` | "LinkedIn carousel" | Preferred format |
| `goal` | "Awareness" | Campaign goal |
| `source` | "Manual topic" | Where the topic came from |
| `context` | "" | Additional context/direction |

**Processing pipeline:**
1. Builds system prompt from `RH_CONTENT_DNA` + detailed field schema for each idea card
2. Builds user prompt with topic, audience, goal, format, source, context
3. Injects repetition avoidance from `_ideas_history[f"ideas_lab:{domain}"]`
4. Enriches with live data:
   - `web_search.search_indian_finance(topic)` — market context
   - `web_search.search_finance_news(topic)` — latest news
   - `web_search.search_content_trends(topic)` — trending content
   - `google_trends.finance_trends_context(topic)` — Google Trends India
5. Calls `ai_mod.chat_json()` with `max_tokens=6000, temperature=0.85`

**Response — each idea card has these fields:**
```json
{
    "title": "Why your ₹50L FD earns less than inflation — a real-terms calculator",
    "format": "LinkedIn carousel",
    "group": "Social",
    "audience": "Salaried professionals 35-45 with ₹20-50L in FDs...",
    "hook": "Your ₹50L FD earned ₹3.5L in interest last year. Inflation took ₹4.2L. You lost ₹70K in real purchasing power.",
    "angle": "Data-backed",
    "score": 89,
    "cta": "Use our FD vs equity calculator at righthorizons.com/tools",
    "visual_direction": "8-slide carousel: slide 1 bold ₹ hook, slides 2-6 comparison charts...",
    "compliance_reminder": "Add SEBI IA disclaimer. Avoid guaranteed return language...",
    "why_it_works": "Loss aversion bias — showing money LOST in real terms...",
    "slide_flow": ["Slide 1: The ₹50L FD trap", "Slide 2: What inflation actually costs you", ...],
    "scores": {
        "Audience fit": 88,
        "Clarity": 85,
        "Platform fit": 82,
        "Conversion potential": 84,
        "Compliance safety": 90
    },
    "platform_notes": "LinkedIn algorithm favors carousels with 8-12 slides posted Tue-Thu 8-10am IST",
    "content_pillar": "Retirement Planning"
}
```

#### `POST /api/ideas/lab/webinar`

**Purpose:** Repurpose webinar content into 15-18 diverse content pieces.

**Request body:** `{"text": "webinar transcript or notes...", "domain": "rh"}`

**Output content mix:** 3-4 LinkedIn posts, 3 carousels, 3 short videos, 2 blog articles, 2 email sequences, 2 quote cards.

**Each item includes:** title, format, funnel_stage (TOFU/MOFU/BOFU), priority (high/medium/low), effort (quick/moderate/substantial), description (80+ words), hook, key_insight, compliance_note.

#### `POST /api/ideas/lab/seo`

**Purpose:** Generate SEO-driven content plans from target keywords.

**Request body:** `{"keywords": "NRI tax planning\nretirement corpus calculator\n...", "domain": "rh"}`

**Each item includes:** title, format, keyword, search_intent, difficulty_tier, funnel_stage, description (100+ words with H2/H3 structure), long_tail_keywords, meta_description, cta, estimated_word_count, content_pillar.

#### `POST /api/ideas/lab/expand`

**Purpose:** Expand a single idea card into a full production asset.

**Request body:**
```json
{
    "idea": { /* full idea object */ },
    "output_type": "brief" | "carousel" | "blog" | "caption",
    "domain": "rh"
}
```

**Output types:**
- **brief**: Overview, target audience, key messages, content structure, visual mood, distribution plan, metrics, SEO notes
- **carousel**: Slide-by-slide content with headlines, body text, visual notes, speaker notes, design system, caption
- **blog**: Meta title/description, full section outline with subheadings, FAQ schema, internal links, featured snippet target
- **caption**: Ready-to-post LinkedIn/Instagram/Twitter captions + email subject lines

#### `GET /api/ideas/lab/seasonal`

**Purpose:** Generate 10 seasonal/timely content ideas for the next 3 months.

**Query params:** `domain`, `month` (optional, defaults to current)

**Considers:** Indian festivals, tax deadlines, market events, NRI-specific timing, life events, regulatory deadlines.

**Each item includes:** title, format, occasion, timing (exact publishing window), description, audience, urgency (high/medium/low), content_pillar.

#### `GET /api/ideas/generate` (Legacy)

**Purpose:** Simpler idea generation (10 ideas, less detailed than lab/generate).

**Query params:** `domain`, `category` (default "all")

#### `GET /api/ideas/notifications` / `POST /api/ideas/seen`

**Purpose:** Track notification badge count for new ideas.

### 4.3 Frontend — Ideas Lab UI

**Location:** `static/index.html` (line ~597) + `static/app.js` (line ~1986)

**Tab structure:**
```
div#view-ideas
├── Tab buttons: Generate | Library | Seasonal | Webinar | SEO
│
├── section#il-tab-generate (default active)
│   ├── Brief form (2-column grid):
│   │   ├── select#il-client      (domain: RH/PMS/AIF/Akeana)
│   │   ├── select#il-goal        (Awareness/Lead gen/Engagement/...)
│   │   ├── select#il-type        (LinkedIn carousel/Instagram Reel/Blog/...)
│   │   ├── select#il-source      (Manual topic/SEO keyword/Webinar/Trend/...)
│   │   ├── input#il-topic        (core topic text)
│   │   ├── input#il-audience     (target audience text)
│   │   └── textarea#il-context   (additional context)
│   ├── Button: "✦ Generate ideas" → generateILIdeas()
│   ├── KPI metrics bar: Ideas generated | Top score | Saved count | Best fit format
│   ├── Filter chips: All | Social | Video | Blog | Seasonal
│   ├── div#il-idea-grid          (card grid, 3 columns)
│   └── aside#il-drawer           (slide-out detail panel)
│       ├── Idea title, format, audience, badges
│       ├── Hook, Strategic rationale, Content flow (numbered steps)
│       ├── Visual direction, Platform strategy, CTA, Compliance
│       ├── Score breakdown (bar chart: 5 dimensions)
│       └── "Expand with AI" buttons: Full brief | Carousel slides | Blog outline | Captions
│
├── section#il-tab-library
│   └── div#il-library-grid       (saved ideas from localStorage)
│
├── section#il-tab-seasonal
│   └── div#il-seasonal-grid      (AI-generated seasonal ideas)
│
├── section#il-tab-webinar
│   ├── textarea#il-webinar-text  (paste webinar content)
│   ├── Button: "Repurpose webinar" → generateILWebinarIdeas()
│   ├── KPI breakdown (format counts)
│   └── div#il-webinar-grid       (repurposed content cards)
│
└── section#il-tab-seo
    ├── textarea#il-seo-text      (enter SEO keywords, one per line)
    ├── Button: "Generate SEO ideas" → generateILSeoIdeas()
    └── div#il-seo-grid           (SEO content plan cards)
```

**Key JS state variables:**
```javascript
let _ilIdeas = [];           // Current batch of generated ideas
let _ilSavedIdeas = [];      // Persisted in localStorage (key: 'idea_lab_saved_ideas')
let _ilSelectedId = null;    // Currently selected idea in drawer
let _ilFilter = 'All';       // Active format filter
const IL_LS_KEY = 'idea_lab_saved_ideas';
```

**Key JS functions:**

| Function | Purpose |
|----------|---------|
| `switchILTab(tab)` | Switch between generate/library/seasonal/webinar/seo tabs |
| `setILFilter(f)` | Filter idea grid by group (All/Social/Video/Blog/Seasonal) |
| `generateILIdeas()` | Main generate flow — reads brief form, calls API, renders cards |
| `_ilRenderIdeas()` | Renders the idea card grid with current filter |
| `openILDrawer(id)` | Opens slide-out detail panel for an idea |
| `_ilRenderDetail(x)` | Populates the detail panel with full idea info + expand buttons |
| `saveILIdea(id)` | Saves idea to localStorage library |
| `copyILIdea(id)` | Copies idea summary to clipboard |
| `expandILIdea(id, type)` | Calls `/api/ideas/lab/expand` and renders result in drawer |
| `generateILWebinarIdeas()` | Calls webinar repurposing API |
| `generateILSeoIdeas()` | Calls SEO ideas API |
| `generateILSeasonalAI()` | Calls seasonal ideas API (auto-called on tab switch) |
| `_ilGenerateFallbackIdeas()` | Client-side fallback if AI call fails |
| `resetIdeaLab()` | Clears all state + localStorage |
| `loadILWebinarPreset()` / `loadILSeoPreset()` | Pre-fill brief form with preset values |

**Fallback system:** If the AI API call fails, `_ilGenerateFallbackIdeas()` generates 6 template-based ideas using the user's topic/audience inputs, so the UI is never empty.

---

## 5. AI Module (`ai.py`)

### 5.1 Architecture

```
ai.py
├── chat(system, user, max_tokens, temperature) → raw text
├── chat_json(system, user, max_tokens, temperature) → parsed JSON
├── chat_vision(system, user, image_data_url) → raw text
└── chat_vision_json(system, user, image_data_url) → parsed JSON
```

### 5.2 Provider: OpenRouter

- **API URL:** `https://openrouter.ai/api/v1/chat/completions`
- **Primary model:** `anthropic/claude-sonnet-4`
- **Fallback model:** `anthropic/claude-haiku-4` (used when primary returns 400/404)
- **Auth:** Bearer token via `OPENROUTER_API_KEY` env var

### 5.3 JSON Parsing Pipeline

AI responses often have syntax issues. The parsing pipeline is:

1. **Strip markdown fences** — removes ````json ... ````
2. **Direct `json.loads()`** — try raw text
3. **Slice to JSON bounds** — find first `[` or `{` to last `]` or `}`
4. **Basic repair** — remove trailing commas, fix smart quotes, close unclosed brackets
5. **AI repair** — if all else fails, send broken JSON to the AI model with `response_format: json_object` to fix it
6. **Final basic repair on AI-repaired output**

### 5.4 `chat_json()` Specifics

Appends to system prompt:
```
IMPORTANT: Respond with ONLY a valid JSON object of the form {"items": [...]}
where items is the array described above. Escape all double quotes inside
string values as \". Use straight quotes only, no curly/smart quotes.
No markdown, no code fences, no commentary.
```

Uses `response_format: {"type": "json_object"}` in the API payload.

### 5.5 Retry Logic

- Retries on 429, 500, 502, 503, 529 with exponential backoff (1s, 2s)
- Max 3 attempts total
- Connection errors also retry with same backoff

---

## 6. Live Context Enrichment

Both Calendar and Ideas Lab inject real-time data into AI prompts.

### 6.1 Tavily Web Search (`web_search.py`)

**API:** `https://api.tavily.com/search` (requires `TAVILY_API_KEY`)

**Functions used:**

| Function | Query Pattern | Used By |
|----------|--------------|---------|
| `search_market_context()` | "India stock market Nifty Sensex RBI..." | Calendar |
| `search_finance_news()` | "Moneycontrol LiveMint ET Money..." | Calendar, Ideas Lab |
| `search_indian_finance(topic)` | "{topic} India 2026 SEBI INR" | Ideas Lab |
| `search_content_trends(topic)` | "{topic} trending social media..." | Ideas Lab |
| `search_seasonal_events(months)` | "India {months} events festivals..." | Seasonal Ideas |

**Behavior:** Returns empty string gracefully if API key not set or request fails. Results include source attribution: `[moneycontrol.com] Title: content...`

**Finance site filter:** Queries targeting finance news are scoped to: moneycontrol.com, economictimes.indiatimes.com, livemint.com, etmoney.com, valueresearchonline.com, freefincal.com, tickertape.in, ndtvprofit.com.

### 6.2 Google Trends (`google_trends.py`)

**Library:** `pytrends` (unofficial Google Trends API)

**Functions used:**

| Function | Purpose | Used By |
|----------|---------|---------|
| `trending_searches_india()` | Current trending searches in India | Calendar, Seasonal |
| `finance_trends_context(topic)` | Related topics + queries for a keyword | Calendar, Ideas Lab |
| `related_topics(keyword)` | Rising & top related topics (7-day window, geo=IN) | Internal |
| `related_queries(keyword)` | Rising & top related queries | Internal |

**Configuration:** `hl='en-IN', tz=330` (IST timezone offset)

**Behavior:** Returns empty string on any failure (rate limits, network). All operations are India-scoped (`geo='IN'`).

---

## 7. Data Storage & Persistence

### 7.1 Server-Side (In-Memory)

All server-side storage is **in-memory Python dicts** — data is lost on server restart/redeploy.

```python
_calendars: dict = {}          # key: "{domain}:{month}" → list of item dicts
_calendar_history: dict = {}   # key: domain → list of past post titles (up to 200)
_ideas_history: dict = {}      # key: domain → list of past idea titles (up to 200)
_generation_level: dict = {}   # key: domain → int (generation counter)
_ideas_state = {"last_check": 0, "available": 0}  # notification counter
```

**Key patterns:**
- Calendar key format: `"rh:2026-07"` — domain + month
- Ideas history key format: `"ideas_lab:rh"` or `"ideas:rh"` — feature + domain
- History stores last 200 entries per domain (sliding window)

### 7.2 Client-Side (localStorage)

```javascript
const IL_LS_KEY = 'idea_lab_saved_ideas';
// Stores: JSON array of saved idea objects
// Persists across page reloads, survives server restarts
// Cleared by resetIdeaLab()
```

### 7.3 Implications for Replication

If you need persistence across deploys:
- Replace `_calendars` with a database (Supabase, PostgreSQL, MongoDB)
- Replace `_calendar_history` / `_ideas_history` with a DB table
- Keep localStorage for the "saved library" (it's client-specific by design)

---

## 8. Repetition Avoidance System

This is a critical system that prevents the AI from generating the same content repeatedly.

### 8.1 How It Works

```python
def _push_history(store, domain, items, key_field="title"):
    """After each generation, extract titles and push to history."""
    for item in items:
        title = item.get(key_field) or item.get("caption") or item.get("description")
        swimlane = item.get("swimlane", "")
        store[domain].append({"title": title[:200], "swimlane": swimlane})
    store[domain] = store[domain][-200:]  # Keep last 200

def _history_context(store, domain, limit=60):
    """Before each generation, format past items as a 'do not repeat' block."""
    past = store[domain][-limit:]
    lines = [f"- {p['title']} [{p['swimlane']}]" for p in past]
    return "\n".join(lines)
```

### 8.2 Injection into Prompts

```
DO NOT REPEAT THESE PAST POSTS (vary the angle, the numbers, the specifics):
- Why your ₹50L FD earns less than inflation [Retirement Planning]
- NRI tax residency: 3 rules that changed in 2026 [NRI]
- ...

Produce ALL-NEW angles. If a swimlane needs to be covered again,
shift the sub-topic, audience segment, age bracket, or numerical example.
```

### 8.3 Generation Level System

```python
def _level_up(domain):
    _generation_level[domain] = _generation_level.get(domain, 0) + 1
    return _generation_level[domain]
```

Injected as:
```
GENERATION LEVEL: 5 (each level must go deeper / more specialized than the last)
LEVEL-UP RULES:
- Level 1-3: foundational topics
- Level 4-7: intermediate angles with concrete math
- Level 8+: advanced/niche (estate freezes, GIFT City FoF structures, ...)
```

This ensures content gets progressively more sophisticated with each generation.

---

## 9. Frontend Architecture

### 9.1 Navigation

Both Calendar and Ideas Lab are tab views managed by a simple show/hide system:

```javascript
['dashboard', 'analytics', 'calendar', 'ideas', 'validator', 'reports', 'settings'].forEach(v => {
    // Toggle display:none on div#view-{tab}
});
```

### 9.2 API Helper

All API calls go through a shared `api()` function:

```javascript
async function api(url, options = {}) {
    const resp = await fetch(url, options);
    if (!resp.ok) throw new Error(await resp.text());
    return resp.json();
}
```

### 9.3 Idea Card Component

Each idea renders as an `<article class="il-idea-card">` with:
- Purple badge (format), green badge (angle)
- Score circle (CSS custom property `--score`)
- Title, hook preview
- Action buttons: Save, Copy, View brief

### 9.4 Detail Drawer

The drawer is a CSS slide-out panel (`aside.il-drawer`) with a backdrop overlay. Opens on card click, closes on backdrop click or close button. Contains the full idea brief + "Expand with AI" buttons.

### 9.5 Skeleton Loading

During API calls, skeleton placeholders are shown:
```javascript
grid.innerHTML = Array(6).fill('<div class="il-skeleton"></div>').join('');
```

### 9.6 Toast Notifications

```javascript
function _ilToast(msg) {
    // Shows a temporary notification at the bottom of the Ideas Lab
}
```

---

## 10. Domain Filtering

### 10.1 Domain Configuration (`config.py`)

```python
DOMAINS = {
    "rh": {"label": "Right Horizons", "short": "RH", ...},
    "pms": {"label": "Right Horizons PMS", "short": "PMS", ...},
    "aif": {"label": "Right Horizons AIF", "short": "AIF", ...},
    "akeana": {"label": "Akeana", "short": "AKE", ...},
}
```

### 10.2 How Domain Affects Output

- **Calendar:** System prompt references the domain label; history is tracked per domain; storage key includes domain (`rh:2026-07`)
- **Ideas Lab:** Domain passed as query param; AI tailors content to the entity type (Investment Advisory vs PMS vs AIF); web searches include domain context
- **Client selector:** `<select id="il-client">` in the Ideas Lab UI lets users switch domains; Calendar uses the global `currentDomain` variable

### 10.3 Frontend Domain Variable

```javascript
let currentDomain = 'rh';  // Set by domain selector in nav bar
// Calendar reads: currentDomain
// Ideas Lab reads: document.getElementById('il-client').value
```

---

## 11. Replication Checklist

To implement these features in another dashboard:

### Backend

- [ ] Set up OpenRouter account + API key (or swap for direct Anthropic/OpenAI API)
- [ ] Create `ai.py` equivalent with `chat_json()` function + JSON repair pipeline
- [ ] Set up Tavily API key for web search enrichment (optional but recommended)
- [ ] Install `pytrends` for Google Trends (optional)
- [ ] Write your **Content DNA** — the detailed brand voice/style document (this is the most impactful piece)
- [ ] Create calendar endpoints: generate, get, save, export CSV, upload
- [ ] Create ideas endpoints: generate, webinar, SEO, expand, seasonal
- [ ] Implement repetition avoidance: history tracking + injection into prompts
- [ ] Implement generation level system for progressive depth
- [ ] Implement variety seed system (random devices/personas/angles)
- [ ] Replace in-memory dicts with a database if you need persistence

### Frontend

- [ ] Create tab navigation system
- [ ] Build calendar UI: month picker, generate button, editable table, CSV download, file upload
- [ ] Build Ideas Lab UI: brief form, card grid, detail drawer, filter chips, KPI metrics
- [ ] Build sub-tabs: Library (localStorage), Seasonal, Webinar, SEO
- [ ] Implement fallback idea generation (client-side) for when AI fails
- [ ] Add skeleton loading states
- [ ] Add toast notifications

### Environment Variables

```bash
OPENROUTER_API_KEY=...       # Required — AI generation
TAVILY_API_KEY=...           # Optional — live web search context
# Google Trends uses pytrends (no API key needed, but may hit rate limits)
```

### Python Dependencies

```
fastapi
uvicorn
requests
pydantic
openpyxl        # Excel parsing for calendar upload
pypdf           # PDF parsing for calendar upload
python-docx     # DOCX parsing for calendar upload
pytrends        # Google Trends
```

---

## Architecture Decisions & Trade-offs

| Decision | Rationale | Alternative |
|----------|-----------|-------------|
| In-memory storage | Simplest for serverless (Vercel); calendar is regenerable | Use Supabase/PostgreSQL for persistence |
| OpenRouter as AI proxy | Access multiple models with one key; easy fallback | Direct Anthropic API for lower latency |
| `response_format: json_object` | Forces structured output | Function calling / tool use |
| JSON repair pipeline | LLMs sometimes produce broken JSON | Use a model that supports guaranteed JSON |
| localStorage for saved library | Client-specific, no auth needed | Server-side with user accounts |
| Vanilla JS (no framework) | Zero build step, minimal dependencies | React/Vue for complex state management |
| Tavily for web search | Simple API, good quality, includes answer synthesis | Serper, SerpAPI, or Google Custom Search |
| Content DNA as string constant | Easy to edit, version-controlled | Database-stored templates for multi-tenant |
