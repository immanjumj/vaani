import os
import uuid
from datetime import datetime

from briefing.builder import build_script
from briefing.mock_data import get_mock_meetings, get_mock_tasks
from briefing.scout import get_news
from integrations.flagsmith_client import get_user_flags, track_delivered
from integrations.sarvam import text_to_speech, translate_text
from integrations.telegram_bot import send_audio_message

# In-memory session store: session_id -> briefing payload
# NudgeBee's prepare → approve → send flow uses this
_sessions: dict[str, dict] = {}


async def prepare_briefing(user_id: str) -> str:
    flags = get_user_flags(user_id)
    language = flags["language"]
    fmt = flags["briefing_format"]

    tasks = get_mock_tasks(fmt) if flags["show_tasks"] else []
    meetings = get_mock_meetings(fmt) if flags["show_meetings"] else []
    news = await get_news(fmt) if flags["show_news"] else []

    script = build_script(tasks, meetings, news, language, fmt)

    if language != "en-IN":
        script = await translate_text(script, language)

    audio = await text_to_speech(script, language)

    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "audio": audio,
        "script": script,
        "user_id": user_id,
        "language": language,
        "format": fmt,
        "prepared_at": datetime.utcnow().isoformat(),
    }
    return session_id


async def send_briefing(session_id: str) -> None:
    if session_id not in _sessions:
        raise KeyError(f"Session {session_id!r} not found or already sent")

    session = _sessions.pop(session_id)
    caption = (
        f"Vaani Morning Briefing — "
        f"{session['language']} · {session['format']} format · "
        f"{datetime.now().strftime('%d %b %Y, %I:%M %p')}"
    )
    await send_audio_message(session["audio"], caption)
    track_delivered(session["user_id"])


async def run_briefing(user_id: str | None = None) -> None:
    uid = user_id or os.getenv("VAANI_USER_ID", "default_user")
    session_id = await prepare_briefing(uid)
    await send_briefing(session_id)
