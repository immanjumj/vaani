#!/usr/bin/env python3
"""
make_demo.py — Generate a Vaani demo video with Sarvam TTS voiceover.

Usage:
  source .venv/bin/activate
  python3 make_demo.py

Output: vaani_demo.mp4
"""

import asyncio
import base64
import io
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
if not SARVAM_API_KEY:
    raise SystemExit("SARVAM_API_KEY not set — check your .env file")

SITE_URL = "https://vaani.signalnook.in"
OUTPUT = Path("vaani_demo.mp4")
PAUSE_BETWEEN = 0.6   # seconds of silence between segments
VIEWPORT = {"width": 1280, "height": 720}

SEGMENTS = [
    {
        "id": "hero",
        "selector": None,
        "text": (
            "Vaani is an AI morning briefing that speaks your language. "
            "Every day at 7 AM, it gathers your tasks, meetings, and top news — "
            "and delivers them as a personalised audio podcast directly to your Telegram."
        ),
    },
    {
        "id": "how-it-works",
        "selector": "#how",
        "text": (
            "The workflow runs in three steps. "
            "NudgeBee fires the morning trigger and waits for a human reviewer to approve the briefing. "
            "Once approved, Sarvam AI translates the content and generates natural speech. "
            "The audio is then delivered straight to Telegram."
        ),
    },
    {
        "id": "tech-stack",
        "selector": "#tools",
        "text": (
            "Three tools make it all work together. "
            "Flagsmith handles personalisation — managing language settings and running live A-B experiments on briefing formats. "
            "Sarvam AI provides the language model, translation across Indian languages, and voice synthesis. "
            "NudgeBee orchestrates the full pipeline with scheduling, an approval gate, and automatic retries."
        ),
    },
    {
        "id": "languages",
        "selector": "#languages",
        "text": (
            "Vaani speaks eleven Indian languages — "
            "Hindi, Kannada, Tamil, Telugu, Bengali, Marathi, Gujarati, Punjabi, and more — "
            "each with a dedicated regional voice from Sarvam's Bulbul text-to-speech model."
        ),
    },
    {
        "id": "demo",
        "selector": "#demo",
        "text": (
            "Vaani is open source. "
            "You can trigger a briefing from the REST API or message the Telegram bot directly. "
            "Try it now at vaani dot signalnook dot in."
        ),
    },
]


# ── Audio helpers ──────────────────────────────────────────────────────────────

def _chunk(text: str, max_chars: int = 490) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_chars:
            chunks.append(text.strip())
            break
        split_at = text.rfind(" ", 0, max_chars)
        if split_at < max_chars // 2:
            split_at = max_chars
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    return chunks or [text[:max_chars]]


def _wav_duration(wav_bytes: bytes) -> float:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def _concat_wavs(wavs: list[bytes]) -> bytes:
    if len(wavs) == 1:
        return wavs[0]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        for i, w in enumerate(wavs):
            with wave.open(io.BytesIO(w), "rb") as inp:
                if i == 0:
                    out.setparams(inp.getparams())
                out.writeframes(inp.readframes(inp.getnframes()))
    return buf.getvalue()


def _make_silence(duration: float, sample_rate: int = 22050) -> bytes:
    n_frames = int(sample_rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


async def generate_tts(text: str) -> bytes:
    chunks = _chunk(text)
    all_audio = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(chunks), 3):
            batch = chunks[i : i + 3]
            resp = await client.post(
                "https://api.sarvam.ai/text-to-speech",
                headers={"API-Subscription-Key": SARVAM_API_KEY},
                json={
                    "inputs": batch,
                    "target_language_code": "en-IN",
                    "speaker": "simran_en_narration",
                    "model": "bulbul:v4-flash",
                },
            )
            resp.raise_for_status()
            all_audio.extend(base64.b64decode(a) for a in resp.json()["audios"])
    return _concat_wavs(all_audio)


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    from playwright.async_api import async_playwright

    tmpdir = Path(tempfile.mkdtemp(prefix="vaani_demo_"))
    print(f"Working in {tmpdir}\n")

    # 1. Generate TTS for all segments in parallel
    print("Generating voiceover (Sarvam Bulbul TTS)...")
    audio_wavs = await asyncio.gather(*[generate_tts(s["text"]) for s in SEGMENTS])
    durations = [_wav_duration(w) for w in audio_wavs]

    for seg, dur in zip(SEGMENTS, durations):
        print(f"  [{seg['id']:16s}] {dur:.1f}s")

    # 2. Build combined audio track (segments interleaved with silence)
    silence = _make_silence(PAUSE_BETWEEN)
    parts = []
    for i, wav in enumerate(audio_wavs):
        parts.append(wav)
        if i < len(audio_wavs) - 1:
            parts.append(silence)

    combined_wav = tmpdir / "audio.wav"
    combined_wav.write_bytes(_concat_wavs(parts))
    total_audio = sum(durations) + PAUSE_BETWEEN * (len(SEGMENTS) - 1)
    print(f"\n  Total audio: {total_audio:.1f}s\n")

    # 3. Take screenshots via Playwright
    print("Capturing screenshots of vaani.signalnook.in ...")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport=VIEWPORT)
        await page.goto(SITE_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        frames = []
        for i, seg in enumerate(SEGMENTS):
            if seg["selector"]:
                el = await page.query_selector(seg["selector"])
                if el:
                    await el.scroll_into_view_if_needed()
                    await page.wait_for_timeout(700)
                else:
                    print(f"  Warning: selector '{seg['selector']}' not found, using current view")

            img_path = tmpdir / f"frame_{i:02d}.png"
            await page.screenshot(path=str(img_path), full_page=False)
            frames.append(img_path)
            print(f"  [{seg['id']:16s}] captured")

        await browser.close()

    # 4. Build ffmpeg concat list
    # Each screenshot displays for its audio duration + silence gap
    # (last segment gets no trailing silence)
    display_times = [
        dur + (PAUSE_BETWEEN if i < len(SEGMENTS) - 1 else 0)
        for i, dur in enumerate(durations)
    ]

    concat_txt = tmpdir / "concat.txt"
    with concat_txt.open("w") as f:
        for img, t in zip(frames, display_times):
            f.write(f"file '{img}'\n")
            f.write(f"duration {t:.4f}\n")
        f.write(f"file '{frames[-1]}'\n")  # ffmpeg quirk: repeat last without duration

    # 5. Render silent video from screenshots
    print("\nRendering video...")
    video_silent = tmpdir / "video_silent.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-vf", (
                f"scale={VIEWPORT['width']}:{VIEWPORT['height']}:"
                "force_original_aspect_ratio=decrease,"
                f"pad={VIEWPORT['width']}:{VIEWPORT['height']}:"
                "(ow-iw)/2:(oh-ih)/2:color=white,"
                "format=yuv420p"
            ),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-r", "30",
            str(video_silent),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # 6. Mux video + audio → final MP4
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(video_silent),
            "-i", str(combined_wav),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest",
            str(OUTPUT),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    shutil.rmtree(tmpdir)
    print(f"\nDone!  →  {OUTPUT.resolve()}")
    print(f"Duration: ~{total_audio:.0f}s")


if __name__ == "__main__":
    asyncio.run(main())
