import base64
import io
import os
import wave

import httpx

_SARVAM_BASE = "https://api.sarvam.ai"
_MAX_CHARS = 1500  # Bulbul safe limit per chunk


def _auth_headers() -> dict:
    return {"API-Subscription-Key": os.environ["SARVAM_API_KEY"]}


def _chunk_text(text: str, max_chars: int = _MAX_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks, current = [], ""
    for sentence in text.replace(". ", ".|").split("|"):
        if len(current) + len(sentence) > max_chars:
            if current:
                chunks.append(current.strip())
            current = sentence
        else:
            current += sentence
    if current.strip():
        chunks.append(current.strip())
    return chunks or [text[:max_chars]]


def _concat_wavs(wav_list: list[bytes]) -> bytes:
    if len(wav_list) == 1:
        return wav_list[0]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        for i, wav_bytes in enumerate(wav_list):
            with wave.open(io.BytesIO(wav_bytes), "rb") as inp:
                if i == 0:
                    out.setparams(inp.getparams())
                out.writeframes(inp.readframes(inp.getnframes()))
    return buf.getvalue()


async def translate_text(text: str, target_language: str) -> str:
    if target_language == "en-IN":
        return text
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{_SARVAM_BASE}/translate",
            headers=_auth_headers(),
            json={
                "input": text,
                "source_language_code": "en-IN",
                "target_language_code": target_language,
                "speaker_gender": "Female",
                "mode": "formal",
            },
        )
        resp.raise_for_status()
        return resp.json()["translated_text"]


async def text_to_speech(text: str, language_code: str = "en-IN") -> bytes:
    chunks = _chunk_text(text)
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{_SARVAM_BASE}/text-to-speech",
            headers=_auth_headers(),
            json={
                "inputs": chunks,
                "target_language_code": language_code,
                "speaker": "meera",
                "model": "bulbul:v4",
                "enable_preprocessing": True,
            },
        )
        resp.raise_for_status()
        audio_list = [base64.b64decode(a) for a in resp.json()["audios"]]
    return _concat_wavs(audio_list)
