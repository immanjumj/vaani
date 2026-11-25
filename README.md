# Vaani — AI Morning Briefing

> Every morning at 7 AM, Vaani delivers a personalised audio briefing in your language — your tasks, today's meetings, and live news — straight to Telegram as a podcast.

**[Live site](https://vaani.signalnook.in) · [Demo video](#demo-video)**

---

## Demo Video

<!-- Upload vaani_demo.mp4 to YouTube/Loom and paste the link below -->
> _Demo video link coming soon_

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

**Sponsor tool roles (all load-bearing):**
- **Sarvam AI** — Bulbul v4 TTS in 10 Indian languages + Translate API for regional languages. Remove it → no audio, no product.
- **Flagsmith** — remote config (language, content blocks) + multivariate A/B experiment (`briefing_format`: short vs full). Conversion metric: `briefing_delivered`. Remove it → hardcoded behaviour, no experimentation.
- **NudgeBee** — scheduled workflow, human approval gate before sending, automatic retry + alert if Vaani's `/health` goes down. Remove it → no orchestration, no reliability loop.

---

## Flagsmith Setup

Create the following flags in your Flagsmith project:

| Flag name | Type | Default value | Purpose |
|---|---|---|---|
| `user_language` | Remote Config (String) | `en-IN` | Language for TTS. Options: `hi-IN`, `kn-IN`, `ta-IN`, `bn-IN`, etc. |
| `show_tasks` | Feature Flag (Boolean) | `true` | Include tasks section |
| `show_meetings` | Feature Flag (Boolean) | `true` | Include meetings section |
| `show_news` | Feature Flag (Boolean) | `true` | Include news section |
| `briefing_format` | **Multivariate (String)** | `full` (50%) + `short` (50%) | A/B experiment — conversion: `briefing_delivered` |

For the `briefing_format` experiment:
1. Create as a **Multivariate** flag
2. Control value: `full`, Weight: 50%
3. Variant 1 value: `short`, Weight: 50%
4. Enable **Experimentation** and set conversion event to `briefing_delivered`

---

## NudgeBee Workflow Setup

1. Sign up at [app.nudgebee.com](https://app.nudgebee.com)
2. Create a new **Workflow** → name it `Vaani Morning Briefing`
3. Add steps:

   | Step | Type | Config |
   |---|---|---|
   | 1 | **Schedule** | Daily at 07:00 AM IST |
   | 2 | **HTTP Task** | POST `https://<your-ngrok-or-domain>/webhook/nudgebee` · Body: `{"action":"prepare","user_id":"default_user"}` |
   | 3 | **Human Approval Gate** | Prompt: "Vaani briefing is ready. Send to Telegram?" |
   | 4 | **HTTP Task** | POST `.../webhook/nudgebee` · Body: `{"action":"send","session_id":"{{step2.session_id}}"}` |

4. Enable the workflow. If step 2 fails, NudgeBee retries and pages you.

> For the demo, use `{"action":"trigger"}` in step 2 to skip the approval gate and send in one shot.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
SARVAM_API_KEY=          # From https://dashboard.sarvam.ai
FLAGSMITH_ENVIRONMENT_KEY=  # From your Flagsmith project settings
TELEGRAM_BOT_TOKEN=      # From @BotFather on Telegram
TELEGRAM_CHAT_ID=        # Your personal chat ID (send /start to your bot, then check https://api.telegram.org/bot<TOKEN>/getUpdates)
SCOUT_API_URL=           # Optional: your Scout news API endpoint
VAANI_USER_ID=default_user
```

---

## Run Locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
uvicorn main:app --reload
```

Trigger a briefing manually:
```bash
curl -X POST "http://localhost:8000/trigger?user_id=default_user"
```

Expose to NudgeBee (use ngrok or similar):
```bash
ngrok http 8000
```

---

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | NudgeBee health monitor target |
| `POST` | `/webhook/nudgebee` | NudgeBee workflow webhook (`prepare` / `send` / `trigger`) |
| `POST` | `/trigger?user_id=` | Manual one-shot trigger (dev/demo) |

---

## AI Disclosure

This project was built with the assistance of Claude Code (Anthropic). All code has been reviewed and understood by the team. Architecture, data flow, and integration decisions are the team's own.

---

*Submitted to Festive Hacks × WeAreDevelopers Conference India — November 25, 2026*
