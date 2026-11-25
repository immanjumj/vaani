# Vaani — AI Morning Briefing

**[Live site](https://vaani.signalnook.in) · [Demo video](https://github.com/immanjumj/vaani/raw/main/vaani_demo.mp4)**

---

## What & Why

Most people in India start their morning scrolling through three different apps — a task manager, a calendar, and a news feed — across three different languages depending on who built the app. Vaani collapses that into a single two-minute audio podcast delivered to Telegram at 7 AM, in whichever Indian language you prefer.

You don't read it. You listen to it. While making chai.

**Vaani gives you:**
- Your pending tasks, today's meetings, and live news headlines — compiled automatically
- A natural-sounding voice in Hindi, Kannada, Tamil, Telugu, Bengali, Marathi, Gujarati, Punjabi, or English (India)
- A human-in-the-loop approval gate so the briefing is reviewed before it reaches you
- A/B experimentation on briefing length, tracked via real conversion events

---

## Demo Video

[Watch the demo (70s)](https://github.com/immanjumj/vaani/raw/main/vaani_demo.mp4) — shows the full NudgeBee → Sarvam → Telegram pipeline running live with Sarvam voiceover.

---

## Tech Stack & Prerequisites

| Layer | Tool | Version |
|---|---|---|
| Runtime | Python | 3.11+ |
| Web framework | FastAPI + Uvicorn | 0.111 / 0.29 |
| Voice & LLM | Sarvam AI (Bulbul TTS, Mayura Translate, Sarvam-M) | API v1 |
| Personalisation | Flagsmith | SDK 6.x |
| Orchestration | NudgeBee | Workflow builder |
| Delivery | Telegram Bot API | — |
| HTTP client | httpx | 0.27+ |

**You need accounts at:** [Sarvam AI](https://dashboard.sarvam.ai) · [Flagsmith](https://app.flagsmith.com) · [NudgeBee](https://app.nudgebee.com) · Telegram (@BotFather)

---

## Architecture

```
NudgeBee (7 AM schedule)
    │
    ├─ POST /webhook/nudgebee {"action":"prepare"}
    │       │
    │       ├─ Flagsmith  →  language + content blocks + A/B briefing format
    │       ├─ Scout API  →  real news feed (falls back to curated mock)
    │       └─ Sarvam AI  →  translate (if non-English) + Bulbul TTS → WAV
    │
    ├─ Human approval gate  (NudgeBee UI)
    │
    └─ POST /webhook/nudgebee {"action":"send", "session_id":"..."}
            │
            └─ Telegram Bot  →  sends WAV audio message to user
```

**Every integration is load-bearing:**
- **Sarvam AI** — Bulbul v4 TTS in 11 Indian languages + Mayura Translate + Sarvam-M LLM. Remove it → no audio, no product.
- **Flagsmith** — remote config (language, content blocks) + multivariate A/B experiment (`briefing_format`: short vs full). Conversion metric: `briefing_delivered`. Remove it → hardcoded behaviour, no experimentation.
- **NudgeBee** — scheduled workflow, human approval gate, automatic retry + alert if `/health` goes dark. Remove it → no orchestration, no reliability loop.

---

## Quickstart

```bash
git clone https://github.com/immanjumj/vaani.git
cd vaani
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in your keys (see below)
uvicorn main:app --reload
```

Open http://localhost:8000 to see the landing page.

---

## Usage Examples

**Trigger a one-shot briefing:**
```bash
curl -X POST "http://localhost:8000/trigger?user_id=default_user"
# → {"status": "triggered", "user_id": "default_user"}
```

**Run the full NudgeBee simulation (prepare → approve → send):**
```bash
# Step 1 — prepare briefing, get sim_id
curl -X POST http://localhost:8000/simulate/nudgebee/start
# → {"sim_id": "sim_070000", "status": "awaiting_approval", "dashboard_url": "..."}

# Step 2 — open the dashboard URL in a browser, then approve:
curl -X POST http://localhost:8000/simulate/nudgebee/approve/sim_070000
# → {"status": "sent", "message": "Morning briefing delivered to Telegram!"}
```

**Change language via Flagsmith:**  
Set the `user_language` flag to `kn-IN` in your Flagsmith dashboard and trigger again — the next briefing arrives in Kannada.

**Expose to NudgeBee via ngrok:**
```bash
ngrok http 8000
# Use the https://xxxx.ngrok.io URL in your NudgeBee workflow steps
```

---

## Environment Variables

Copy `.env.example` to `.env`:

```env
SARVAM_API_KEY=          # From https://dashboard.sarvam.ai
FLAGSMITH_ENVIRONMENT_KEY=  # From your Flagsmith project settings
TELEGRAM_BOT_TOKEN=      # From @BotFather on Telegram
TELEGRAM_CHAT_ID=        # Send /start to your bot, then GET https://api.telegram.org/bot<TOKEN>/getUpdates
SCOUT_API_URL=           # Optional: news API endpoint (falls back to mock data)
VAANI_USER_ID=default_user
```

---

## Flagsmith Setup

| Flag | Type | Default | Purpose |
|---|---|---|---|
| `user_language` | String | `en-IN` | TTS language (`hi-IN`, `kn-IN`, `ta-IN`, …) |
| `show_tasks` | Boolean | `true` | Include tasks in briefing |
| `show_meetings` | Boolean | `true` | Include meetings |
| `show_news` | Boolean | `true` | Include news |
| `briefing_format` | **Multivariate** | `full` 50% / `short` 50% | A/B experiment — conversion: `briefing_delivered` |

---

## NudgeBee Workflow

| Step | Type | Config |
|---|---|---|
| 1 | Schedule | Daily 07:00 AM IST |
| 2 | HTTP Task | `POST /webhook/nudgebee` `{"action":"prepare","user_id":"default_user"}` |
| 3 | Human Approval Gate | "Vaani briefing ready — send to Telegram?" |
| 4 | HTTP Task | `POST /webhook/nudgebee` `{"action":"send","session_id":"{{step2.session_id}}"}` |

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Landing page |
| `GET` | `/health` | Health check (NudgeBee monitor target) |
| `POST` | `/webhook/nudgebee` | NudgeBee webhook (`prepare` / `send` / `trigger`) |
| `POST` | `/trigger` | Manual one-shot briefing trigger |
| `POST` | `/simulate/nudgebee/start` | Start a demo simulation |
| `GET` | `/simulate/nudgebee/dashboard/{id}` | Live workflow dashboard |
| `POST` | `/simulate/nudgebee/approve/{id}` | Approve and send |

---

## AI Disclosure

Built with Claude Code (Anthropic). Architecture, integration decisions, and all code have been reviewed and are understood by the author.

---

*Submitted to Festive Hacks × WeAreDevelopers Conference India — November 25, 2026*
