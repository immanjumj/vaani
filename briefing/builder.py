import random
from datetime import datetime

from integrations.sarvam import chat_complete

FESTIVE_CLOSINGS = [
    "Wishing you joy and prosperity this festive season!",
    "May this festive season bring warmth and success to everything you do.",
    "Celebrate every moment — it is a wonderful time of year!",
]

ORDINALS = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"]

WORDS_PER_MINUTE = 130


async def _expand_news(news_items: list[dict]) -> list[dict]:
    if not news_items:
        return news_items

    lines = "\n".join(
        f"[{item['topic']}] {item['title']} (Source: {item.get('source', '')})"
        for item in news_items
    )
    prompt = f"""You are writing content for an audio podcast morning briefing. For each headline below, write exactly 2 natural, engaging sentences of spoken commentary that a presenter would say. Keep it conversational, informative, and suitable to be read aloud.

Headlines:
{lines}

Format your response as numbered entries matching the input order:
1. <2-sentence commentary>
2. <2-sentence commentary>
...and so on."""

    try:
        response = await chat_complete(prompt, max_tokens=1200)
        expansions = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and line[0].isdigit() and ". " in line:
                expansions.append(line.split(". ", 1)[1].strip())

        expanded = []
        for i, item in enumerate(news_items):
            expanded.append({**item, "expansion": expansions[i] if i < len(expansions) else ""})
        return expanded
    except Exception:
        return news_items


def _count_words(text: str) -> int:
    return len(text.split())


async def build_script(
    tasks: list[dict],
    meetings: list[dict],
    news: list[dict],
    language_code: str = "en-IN",
    fmt: str = "full",
    duration_mins: int = 5,
) -> str:
    target_words = duration_mins * WORDS_PER_MINUTE

    now = datetime.now()
    day = now.strftime("%A")
    date_str = now.strftime("%B %d, %Y")

    # Expand news headlines with LLM
    expanded_news = await _expand_news(news)

    parts = []

    # Intro
    parts.append(
        f"Good morning and welcome to your Vaani briefing! "
        f"I am your personal AI morning companion. "
        f"Today is {day}, {date_str}. "
        f"Let me walk you through everything you need to know to start your day strong."
    )

    # Tasks
    if tasks:
        count = len(tasks)
        task_intro = f"Let us start with your tasks. You have {count} pending item{'s' if count > 1 else ''} on your list. "
        task_body = ""
        for i, task in enumerate(tasks):
            prefix = ORDINALS[i] if i < len(ORDINALS) else f"Task {i + 1}"
            priority = task.get("priority", "")
            priority_note = f" This is marked as {priority} priority." if priority else ""
            task_body += f"{prefix}: {task['title']}.{priority_note} "
        parts.append(task_intro + task_body.strip())

    # Meetings
    if meetings:
        meet_intro = "Moving on to your schedule for today. "
        meet_body = ""
        for meeting in meetings:
            attendees = meeting.get("attendees", "")
            attendee_note = f" with {attendees}" if attendees else ""
            meet_body += f"You have {meeting['title']}{attendee_note} at {meeting['time']}. "
        parts.append(meet_intro + meet_body.strip())

    # News
    if expanded_news:
        news_intro = "And now, here are your top stories, curated across your selected topics. "
        news_body = ""
        for i, item in enumerate(expanded_news):
            prefix = ORDINALS[i] if i < len(ORDINALS) else f"Story {i + 1}"
            expansion = item.get("expansion", "")
            topic_label = f"In {item['topic']} news"
            if expansion:
                news_body += f"{prefix}: {topic_label} — {item['title']}. {expansion} "
            else:
                news_body += f"{prefix}: {topic_label} — {item['title']}. "
        parts.append(news_intro + news_body.strip())

    # Festive closing
    parts.append(random.choice(FESTIVE_CLOSINGS))
    parts.append(
        "That is your Vaani briefing for today. "
        "Stay informed, stay ahead, and have an absolutely wonderful day ahead!"
    )

    script = " ".join(parts)

    # If still short of target, add a reflective segment
    if _count_words(script) < target_words and expanded_news:
        bridge = (
            "Before we wrap up, let us take a moment to reflect on what matters most today. "
            "The world is moving fast — in technology, in real estate, and in everyday life. "
            "Your morning briefing is designed to keep you one step ahead, "
            "so you can make confident decisions throughout the day. "
            "Remember to follow up on the high-priority items we covered, "
            "and do check in with your team during today's meetings. "
            "Knowledge is your greatest asset, and you are starting this day well-informed."
        )
        script = script + " " + bridge

    return script
