import io
import os

import httpx


async def send_audio_message(audio_bytes: bytes, caption: str = "") -> dict:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{token}/sendAudio",
            data={"chat_id": chat_id, "caption": caption, "title": "Vaani Morning Briefing"},
            files={"audio": ("vaani_briefing.wav", io.BytesIO(audio_bytes), "audio/wav")},
        )
        resp.raise_for_status()
        return resp.json()
