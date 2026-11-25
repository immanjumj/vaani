import random
from datetime import datetime

FESTIVE_CLOSINGS = [
    "Wishing you joy and prosperity this festive season!",
    "May this festive season bring warmth and success to everything you do.",
    "Celebrate every moment — it's a wonderful time of year!",
]

ORDINALS = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh"]


def build_script(
    tasks: list[dict],
    meetings: list[dict],
    news: list[dict],
    language_code: str = "en-IN",
    fmt: str = "full",
) -> str:
    now = datetime.now()
    day = now.strftime("%A")
    date_str = now.strftime("%B %d, %Y")

    parts = [
        f"Good morning! I'm Vaani, your intelligent morning companion. "
        f"Today is {day}, {date_str}."
    ]

    if tasks:
        count = len(tasks)
        task_text = f"You have {count} pending task{'s' if count > 1 else ''}. "
        for i, task in enumerate(tasks):
            prefix = ORDINALS[i] if i < len(ORDINALS) else f"Task {i + 1}"
            task_text += f"{prefix}: {task['title']}. "
        parts.append(task_text.strip())

    if meetings:
        meeting_text = "Here are today's meetings. "
        for meeting in meetings:
            meeting_text += f"{meeting['title']} at {meeting['time']}. "
        parts.append(meeting_text.strip())

    if news:
        news_text = "And here are your top stories. "
        for i, item in enumerate(news):
            prefix = ORDINALS[i] if i < len(ORDINALS) else f"Story {i + 1}"
            news_text += f"{prefix}: {item['title']}. "
        parts.append(news_text.strip())

    parts.append(random.choice(FESTIVE_CLOSINGS))
    parts.append("Have a wonderful day ahead!")

    return " ".join(parts)
