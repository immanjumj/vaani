import io
import os

import httpx


async def send_message(text: str, chat_id: str | None = None) -> dict:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    cid = chat_id or os.environ["TELEGRAM_CHAT_ID"]
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": cid, "text": text},
        )
        resp.raise_for_status()
        return resp.json()


async def send_audio_message(audio_bytes: bytes, caption: str = "", chat_id: str | None = None) -> dict:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    cid = chat_id or os.environ["TELEGRAM_CHAT_ID"]

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{token}/sendAudio",
            data={"chat_id": cid, "caption": caption, "title": "Vaani Morning Briefing"},
            files={"audio": ("vaani_briefing.wav", io.BytesIO(audio_bytes), "audio/wav")},
        )
        resp.raise_for_status()
        return resp.json()
