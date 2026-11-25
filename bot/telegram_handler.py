import asyncio
import os

import httpx

from bot.intent_parser import parse_intent
from briefing.pipeline import run_briefing_request
from integrations.flagsmith_client import get_user_flags
from integrations.telegram_bot import send_message

_BASE = "https://api.telegram.org"

HELP_TEXT = (
    "Hi! I'm Vaani, your AI morning companion.\n\n"
    "Just tell me what you want in natural language:\n"
    "• Give me a 5 min briefing\n"
    "• 15 min podcast on my topics in Kannada\n"
    "• Give me today's news in Hindi\n"
    "• What are my tasks and meetings?\n\n"
    "I'll generate a personalised audio briefing and send it right here!"
)


async def _handle_message(message: dict) -> None:
    chat_id = str(message.get("chat", {}).get("id", ""))
    text = message.get("text", "").strip()
    user_id = str(message.get("from", {}).get("id", "default_user"))

    if not text or not chat_id:
        return

    if text.startswith("/start") or text.startswith("/help"):
        await send_message(HELP_TEXT, chat_id=chat_id)
        return

    await send_message("Generating your briefing, please wait...", chat_id=chat_id)

    try:
        flags = get_user_flags(user_id)
        intent = await parse_intent(text, flags["language"])

        await run_briefing_request(
            user_id=user_id,
            language=intent["language_code"],
            duration_mins=intent["duration_mins"],
            content_type=intent["content_type"],
            topics=flags["news_topics"],
            chat_id=chat_id,
        )
    except Exception as e:
        await send_message(f"Sorry, something went wrong: {e}", chat_id=chat_id)


async def start_polling() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    offset = 0

    while True:
        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                resp = await client.post(
                    f"{_BASE}/bot{token}/getUpdates",
                    json={"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
                )
                data = resp.json()

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                if "message" in update:
                    asyncio.create_task(_handle_message(update["message"]))

        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(5)
