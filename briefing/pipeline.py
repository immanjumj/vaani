import os
import uuid
from datetime import datetime

from briefing.builder import build_script
from briefing.mock_data import get_mock_meetings, get_mock_tasks
from briefing.scout import get_news
from integrations.flagsmith_client import get_user_flags, track_delivered
from integrations.sarvam import text_to_speech, translate_text
from integrations.telegram_bot import send_audio_message

_sessions: dict[str, dict] = {}


async def run_briefing_request(
    user_id: str,
    language: str | None = None,
    duration_mins: int = 5,
    content_type: str = "all",
    topics: list[str] | None = None,
    chat_id: str | None = None,
) -> None:
    flags = get_user_flags(user_id)
    lang = language or flags["language"]
    fmt = flags["briefing_format"]
    news_topics = topics or flags["news_topics"]

    # 2 news items per minute of podcast
    news_count = max(2, duration_mins * 2)

    tasks = get_mock_tasks(fmt) if content_type in ("all", "personal") else []
    meetings = get_mock_meetings(fmt) if content_type in ("all", "personal") else []
    news = await get_news(news_topics, fmt, news_count) if content_type in ("all", "news") else []

    script = await build_script(tasks, meetings, news, lang, fmt, duration_mins)

    if lang != "en-IN":
        script = await translate_text(script, lang)

    audio = await text_to_speech(script, lang)

    target_chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    caption = f"Vaani — {duration_mins} min {content_type} briefing · {lang}"
    await send_audio_message(audio, caption, chat_id=target_chat_id)
    track_delivered(user_id)


async def prepare_briefing(user_id: str) -> str:
    flags = get_user_flags(user_id)
    language = flags["language"]
    fmt = flags["briefing_format"]

    tasks = get_mock_tasks(fmt) if flags["show_tasks"] else []
    meetings = get_mock_meetings(fmt) if flags["show_meetings"] else []
    news = await get_news(flags["news_topics"], fmt, 10) if flags["show_news"] else []

    script = await build_script(tasks, meetings, news, language, fmt, duration_mins=5)

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
    await run_briefing_request(uid, duration_mins=5)
