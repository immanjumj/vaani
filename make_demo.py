#!/usr/bin/env python3
"""
make_demo.py — Record a live working demo of Vaani with Sarvam TTS voiceover.

Flow:
  1. Start local FastAPI server
  2. Fire simulation API (Sarvam TTS runs server-side while we record landing page)
  3. Playwright records the browser live — landing tour → dashboard → approve → SENT
  4. Generate Sarvam voiceover for the narration
  5. Combine recorded video + voiceover with ffmpeg → vaani_demo.mp4

Usage:
  source .venv/bin/activate
  python3 make_demo.py
"""

import asyncio
import base64
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
if not SARVAM_API_KEY:
    raise SystemExit("SARVAM_API_KEY not set — check your .env file")

PORT = 8787
BASE = f"http://localhost:{PORT}"
OUTPUT = Path("vaani_demo.mp4")

NARRATION = (
    "Let me show you Vaani in action. "
    "Vaani is an AI morning briefing that speaks your language — "
    "tasks, meetings, and live news, delivered as audio to Telegram every morning at 7 AM. "
    "It supports eleven Indian languages, powered by Sarvam's Bulbul text-to-speech. "
    "Now let's trigger a live briefing. "
    "We call the simulation API — Vaani starts fetching tasks, meetings, and news, "
    "then generates a personalised audio script using Sarvam AI. "
    "NudgeBee holds the briefing at a human approval gate before it goes out. "
    "Here it is — ready and waiting for a reviewer to approve. "
    "We click Approve, and Vaani sends the audio to Telegram. "
    "Done. The morning briefing has been delivered. "
    "Try it at vaani dot signalnook dot in."
)


# ── TTS helpers ────────────────────────────────────────────────────────────────

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


def wav_duration(wav_bytes: bytes) -> float:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


# ── Server helpers ─────────────────────────────────────────────────────────────

async def wait_for_server(timeout: int = 30) -> None:
    deadline = time.time() + timeout
    async with httpx.AsyncClient() as client:
        while time.time() < deadline:
            try:
                resp = await client.get(f"{BASE}/health", timeout=2.0)
                if resp.status_code == 200:
                    return
            except Exception:
                pass
            await asyncio.sleep(0.5)
    raise TimeoutError("Server did not start in time")


async def start_simulation() -> str:
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{BASE}/simulate/nudgebee/start")
        resp.raise_for_status()
        return resp.json()["sim_id"]


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    from playwright.async_api import async_playwright

    tmpdir = Path(tempfile.mkdtemp(prefix="vaani_demo_"))
    print(f"Working in {tmpdir}\n")

    # 1. Start local server
    print("Starting Vaani server...")
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", str(PORT), "--log-level", "error"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    await wait_for_server()
    print(f"  Server ready at {BASE}\n")

    try:
        # 2. Pre-start simulation + voiceover BEFORE camera rolls so there's no visible wait
        print("Pre-starting simulation (Sarvam preparing audio off-camera)...")
        sim_task = asyncio.create_task(start_simulation())
        print("Generating voiceover (Sarvam Bulbul TTS)...")
        tts_task = asyncio.create_task(generate_tts(NARRATION))

        # 3. Record browser session live
        print("Recording live demo...\n")
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                slow_mo=120,
                args=["--window-size=1280,720"],
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                record_video_dir=str(tmpdir / "video"),
                record_video_size={"width": 1280, "height": 720},
            )
            (tmpdir / "video").mkdir(exist_ok=True)
            page = await context.new_page()

            # ── Landing page tour ──────────────────────────────────────────
            print("  Landing page...")
            await page.goto(BASE, wait_until="networkidle")
            await page.wait_for_timeout(2500)

            # Scroll through sections — simulation is already running off-camera
            for sel in ["#how", "#tools", "#languages"]:
                await page.evaluate(
                    f"document.querySelector('{sel}')?.scrollIntoView({{behavior:'smooth'}})"
                )
                await page.wait_for_timeout(2200)

            # Simulation should be ready by now (or nearly so)
            print("  Waiting for briefing to be prepared...", end="", flush=True)
            sim_id = await sim_task
            print(f" ready ({sim_id[:8]}...)")

            # ── Simulation dashboard ───────────────────────────────────────
            print("  Opening NudgeBee simulation dashboard...")
            await page.goto(
                f"{BASE}/simulate/nudgebee/dashboard/{sim_id}",
                wait_until="networkidle",
            )
            await page.wait_for_timeout(2000)

            # Wait for AWAITING APPROVAL state (dashboard auto-refreshes)
            print("  Waiting for approval gate...", end="", flush=True)
            for _ in range(30):
                content = await page.content()
                if "AWAITING APPROVAL" in content or "SENT" in content:
                    break
                await page.wait_for_timeout(2500)
            print(" approval gate visible")

            await page.wait_for_timeout(2500)

            # ── Approve ────────────────────────────────────────────────────
            print("  Clicking Approve...")
            btn = await page.query_selector("button[type=submit]")
            if btn:
                await btn.click()
            else:
                # Already sent or no button — just wait
                print("  (button not found, may already be processing)")

            # Wait for SENT
            print("  Waiting for SENT...", end="", flush=True)
            for _ in range(20):
                content = await page.content()
                if "SENT" in content:
                    break
                await page.wait_for_timeout(2500)
            print(" done")

            await page.wait_for_timeout(4000)

            # Finish recording
            video_path_obj = await page.video.path()
            await context.close()
            await browser.close()

        video_webm = Path(video_path_obj)
        print(f"\n  Recorded: {video_webm.name}")

        # 4. Wait for TTS
        print("\nWaiting for voiceover...")
        narration_wav = await tts_task
        narration_duration = wav_duration(narration_wav)
        print(f"  Voiceover: {narration_duration:.1f}s")

        narration_path = tmpdir / "narration.wav"
        narration_path.write_bytes(narration_wav)

        # 5. Convert WebM → MP4 (silent)
        print("\nRendering final video...")
        video_mp4 = tmpdir / "video_silent.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(video_webm),
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
                       "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=white,"
                       "format=yuv420p",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                str(video_mp4),
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

        # 6. Mux video + narration
        # Narration drives the length — if video is shorter, freeze last frame;
        # if longer, narration is cut short. We pad video to match audio length.
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(video_mp4),
                "-i", str(narration_path),
                "-filter_complex",
                "[0:v]tpad=stop_mode=clone:stop_duration=10[v]",
                "-map", "[v]", "-map", "1:a",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest",
                str(OUTPUT),
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    finally:
        server.terminate()
        shutil.rmtree(tmpdir)

    print(f"\nDone!  →  {OUTPUT.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
