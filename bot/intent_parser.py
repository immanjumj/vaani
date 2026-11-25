import json
import re

from integrations.sarvam import chat_complete

LANG_MAP = {
    "kannada": "kn-IN",
    "hindi": "hi-IN",
    "english": "en-IN",
    "tamil": "ta-IN",
    "telugu": "te-IN",
    "bengali": "bn-IN",
    "marathi": "mr-IN",
    "gujarati": "gu-IN",
    "punjabi": "pa-IN",
    "malayalam": "ml-IN",
    "odia": "od-IN",
}


async def parse_intent(text: str, default_language: str = "en-IN") -> dict:
    prompt = f"""Parse this podcast/briefing request. Extract exactly three fields:
- duration_mins: integer (default 5, max 60)
- language_code: IETF tag — one of: en-IN hi-IN kn-IN ta-IN te-IN bn-IN mr-IN gu-IN pa-IN ml-IN od-IN
- content_type: exactly one of "news", "personal", or "all"

Request: "{text}"
Default language if not mentioned: {default_language}

Respond ONLY with valid JSON. Example: {{"duration_mins": 15, "language_code": "kn-IN", "content_type": "all"}}"""

    try:
        response = await chat_complete(prompt, max_tokens=80)
        match = re.search(r"\{.*?\}", response, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            return {
                "duration_mins": int(parsed.get("duration_mins", 5)),
                "language_code": parsed.get("language_code", default_language),
                "content_type": parsed.get("content_type", "all"),
            }
    except Exception:
        pass

    return _regex_parse(text, default_language)


def _regex_parse(text: str, default_language: str) -> dict:
    t = text.lower()

    duration = 5
    m = re.search(r"(\d+)\s*min", t)
    if m:
        duration = min(int(m.group(1)), 60)

    language = default_language
    for name, code in LANG_MAP.items():
        if name in t:
            language = code
            break

    content_type = "all"
    if any(w in t for w in ["news", "stories", "topics", "headlines"]):
        content_type = "news"
    elif any(w in t for w in ["personal", "tasks", "meetings", "schedule", "calendar", "my day"]):
        content_type = "personal"

    return {"duration_mins": duration, "language_code": language, "content_type": content_type}
