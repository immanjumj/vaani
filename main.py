import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

load_dotenv()

from briefing.pipeline import prepare_briefing, run_briefing, send_briefing
from bot.telegram_handler import start_polling

_INDEX_HTML = Path(__file__).parent / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    poll_task = None
    try:
        if os.getenv("TELEGRAM_BOT_TOKEN"):
            poll_task = asyncio.create_task(start_polling())
    except Exception:
        pass
    yield
    if poll_task:
        poll_task.cancel()


app = FastAPI(title="Vaani — AI Morning Briefing", version="1.0.0", lifespan=lifespan)

# In-memory simulation state for NudgeBee demo
_sim_sessions: dict[str, dict] = {}


# ── Landing page ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def landing():
    return _INDEX_HTML.read_text()


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "vaani"}


# ── NudgeBee webhook ──────────────────────────────────────────────────────────

class NudgeBeePayload(BaseModel):
    action: str
    user_id: str = "default_user"
    session_id: str | None = None


@app.post("/webhook/nudgebee")
async def nudgebee_webhook(payload: NudgeBeePayload, background_tasks: BackgroundTasks):
    if payload.action == "prepare":
        session_id = await prepare_briefing(payload.user_id)
        return {"status": "ready", "session_id": session_id,
                "message": "Briefing prepared. Approve in NudgeBee to send."}

    if payload.action == "send":
        if not payload.session_id:
            raise HTTPException(status_code=400, detail="session_id required for send")
        try:
            await send_briefing(payload.session_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        return {"status": "sent"}

    if payload.action == "trigger":
        background_tasks.add_task(run_briefing, payload.user_id)
        return {"status": "triggered"}

    raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action!r}")


# ── NudgeBee Simulation (demo) ────────────────────────────────────────────────

@app.post("/simulate/nudgebee/start")
async def sim_start(user_id: str = "default_user"):
    """Step 1: NudgeBee scheduled trigger — prepares briefing, waits for approval."""
    sim_id = f"sim_{datetime.now().strftime('%H%M%S')}"
    _sim_sessions[sim_id] = {
        "status": "preparing",
        "user_id": user_id,
        "started_at": datetime.now().isoformat(),
        "session_id": None,
        "approved_at": None,
        "sent_at": None,
        "log": [f"[{_ts()}] NudgeBee scheduled trigger fired (07:00 AM IST)"],
    }

    _sim_sessions[sim_id]["log"].append(f"[{_ts()}] Step 1: Fetching tasks, meetings, news via Vaani...")
    session_id = await prepare_briefing(user_id)
    _sim_sessions[sim_id]["session_id"] = session_id
    _sim_sessions[sim_id]["status"] = "awaiting_approval"
    _sim_sessions[sim_id]["log"].append(f"[{_ts()}] Briefing prepared. Session: {session_id[:8]}...")
    _sim_sessions[sim_id]["log"].append(f"[{_ts()}] Step 2: HUMAN APPROVAL GATE — waiting for reviewer...")

    return {"sim_id": sim_id, "status": "awaiting_approval",
            "approve_url": f"/simulate/nudgebee/approve/{sim_id}",
            "dashboard_url": f"/simulate/nudgebee/dashboard/{sim_id}"}


@app.post("/simulate/nudgebee/approve/{sim_id}")
async def sim_approve(sim_id: str):
    """Step 2: Human approves in NudgeBee — triggers send."""
    if sim_id not in _sim_sessions:
        raise HTTPException(status_code=404, detail="Simulation not found")
    sim = _sim_sessions[sim_id]
    if sim["status"] != "awaiting_approval":
        raise HTTPException(status_code=400, detail=f"Cannot approve — status is {sim['status']}")

    sim["status"] = "sending"
    sim["approved_at"] = datetime.now().isoformat()
    sim["log"].append(f"[{_ts()}] APPROVED by reviewer. Proceeding to send...")
    sim["log"].append(f"[{_ts()}] Step 3: Sending briefing to Telegram...")

    await send_briefing(sim["session_id"])

    sim["status"] = "sent"
    sim["sent_at"] = datetime.now().isoformat()
    sim["log"].append(f"[{_ts()}] Briefing delivered to Telegram. Workflow complete.")
    sim["log"].append(f"[{_ts()}] Flagsmith conversion event 'briefing_delivered' tracked.")

    return {"status": "sent", "message": "Morning briefing delivered to Telegram!"}


@app.get("/simulate/nudgebee/dashboard/{sim_id}", response_class=HTMLResponse)
async def sim_dashboard(sim_id: str):
    """Live NudgeBee workflow dashboard for demo."""
    sim = _sim_sessions.get(sim_id, {})
    status = sim.get("status", "not found")
    log_lines = "\n".join(sim.get("log", []))

    status_color = {"preparing": "#f59e0b", "awaiting_approval": "#3b82f6",
                    "sending": "#8b5cf6", "sent": "#10b981"}.get(status, "#6b7280")

    approve_btn = ""
    if status == "awaiting_approval":
        approve_btn = f"""
        <form method="post" action="/simulate/nudgebee/approve/{sim_id}">
            <button type="submit" style="margin-top:16px;padding:12px 32px;background:#10b981;
            color:white;border:none;border-radius:8px;font-size:16px;cursor:pointer;font-weight:bold;">
                ✅ Approve & Send Briefing
            </button>
        </form>
        <p style="color:#6b7280;font-size:13px;margin-top:8px;">
            (In production NudgeBee, this approval gate appears in the NudgeBee workflow UI)
        </p>"""

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Vaani × NudgeBee Workflow</title>
    <meta http-equiv="refresh" content="3">
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #e2e8f0;
               max-width: 800px; margin: 40px auto; padding: 0 20px; }}
        h1 {{ color: #f8fafc; }} h2 {{ color: #94a3b8; font-size: 14px; text-transform: uppercase; }}
        .status {{ display:inline-block; padding: 6px 16px; border-radius: 20px;
                   background: {status_color}22; color: {status_color};
                   border: 1px solid {status_color}; font-weight: bold; font-size: 18px; }}
        .log {{ background: #1e293b; border-radius: 8px; padding: 16px;
                font-family: monospace; font-size: 13px; line-height: 1.8;
                white-space: pre-wrap; color: #94a3b8; margin-top: 16px; }}
        .step {{ display:flex; align-items:center; gap:12px; padding:12px;
                 background:#1e293b; border-radius:8px; margin:8px 0; }}
        .dot {{ width:12px; height:12px; border-radius:50%; flex-shrink:0; }}
    </style>
</head>
<body>
    <h1>🐝 Vaani × NudgeBee Workflow</h1>
    <p>Simulation ID: <code>{sim_id}</code></p>
    <p>Status: <span class="status">{status.upper().replace('_', ' ')}</span></p>

    <h2>Workflow Steps</h2>
    <div class="step">
        <div class="dot" style="background:{'#10b981' if status not in ['preparing'] else '#f59e0b'}"></div>
        <div><strong>Step 1: Schedule Trigger</strong> — NudgeBee fires at 07:00 AM IST</div>
    </div>
    <div class="step">
        <div class="dot" style="background:{'#10b981' if status in ['sending','sent'] else ('#3b82f6' if status == 'awaiting_approval' else '#475569')}"></div>
        <div><strong>Step 2: Prepare Briefing</strong> — Fetch news (Scout), tasks, meetings → Sarvam TTS → Audio ready</div>
    </div>
    <div class="step">
        <div class="dot" style="background:{'#10b981' if status in ['sending','sent'] else ('#f59e0b' if status == 'awaiting_approval' else '#475569')}"></div>
        <div><strong>Step 3: Human Approval Gate</strong> — Reviewer confirms before sending</div>
    </div>
    <div class="step">
        <div class="dot" style="background:{'#10b981' if status == 'sent' else '#475569'}"></div>
        <div><strong>Step 4: Deliver</strong> — Send audio to Telegram + track Flagsmith conversion</div>
    </div>

    {approve_btn}

    <h2 style="margin-top:24px">Live Log</h2>
    <div class="log">{log_lines}</div>
    <p style="color:#475569;font-size:12px;margin-top:8px;">Auto-refreshing every 3 seconds</p>
</body>
</html>"""


@app.post("/trigger")
async def manual_trigger(background_tasks: BackgroundTasks, user_id: str = "default_user"):
    background_tasks.add_task(run_briefing, user_id)
    return {"status": "triggered", "user_id": user_id}


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
