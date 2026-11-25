import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from pydantic import BaseModel

load_dotenv()

from briefing.pipeline import prepare_briefing, run_briefing, send_briefing


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Vaani — AI Morning Briefing", version="1.0.0", lifespan=lifespan)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "vaani"}


# ── NudgeBee webhook ──────────────────────────────────────────────────────────
#
# NudgeBee workflow steps:
#   1. Scheduled HTTP task  →  POST /webhook/nudgebee  {"action": "prepare"}
#   2. Human approval gate  →  reviewer approves in NudgeBee UI
#   3. HTTP task on approve →  POST /webhook/nudgebee  {"action": "send", "session_id": "..."}
#
# If step 1 fails (non-2xx), NudgeBee retries and can page on-call.

class NudgeBeePayload(BaseModel):
    action: str               # "prepare" | "send" | "trigger"
    user_id: str = "default_user"
    session_id: str | None = None


@app.post("/webhook/nudgebee")
async def nudgebee_webhook(payload: NudgeBeePayload, background_tasks: BackgroundTasks):
    if payload.action == "prepare":
        session_id = await prepare_briefing(payload.user_id)
        return {
            "status": "ready",
            "session_id": session_id,
            "message": "Briefing prepared. Approve in NudgeBee to send.",
        }

    if payload.action == "send":
        if not payload.session_id:
            raise HTTPException(status_code=400, detail="session_id required for send")
        try:
            await send_briefing(payload.session_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        return {"status": "sent"}

    if payload.action == "trigger":
        # Single-step: prepare + send immediately (useful for testing)
        background_tasks.add_task(run_briefing, payload.user_id)
        return {"status": "triggered"}

    raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action!r}")


# ── Manual trigger (dev / demo) ───────────────────────────────────────────────

@app.post("/trigger")
async def manual_trigger(
    background_tasks: BackgroundTasks,
    user_id: str = "default_user",
):
    background_tasks.add_task(run_briefing, user_id)
    return {"status": "triggered", "user_id": user_id}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
