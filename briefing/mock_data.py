MOCK_TASKS = [
    {"title": "Review Diwali campaign budget proposal", "priority": "high"},
    {"title": "Confirm gift hamper delivery for 20 clients", "priority": "high"},
    {"title": "Book venue for New Year team dinner", "priority": "medium"},
    {"title": "Send festive greetings to partner organizations", "priority": "medium"},
    {"title": "Review Q4 real estate portfolio report", "priority": "low"},
]

MOCK_MEETINGS = [
    {"title": "Year-end strategy sync", "time": "10:00 AM", "attendees": "Priya, Rahul"},
    {"title": "Client review — festive offers", "time": "2:30 PM", "attendees": "Sales team"},
    {"title": "Project Vaani demo prep", "time": "4:00 PM", "attendees": "Dev team"},
]

MOCK_NEWS = [
    {
        "title": "RBI holds repo rate steady ahead of festive season lending surge",
        "source": "Economic Times",
    },
    {
        "title": "India real estate: housing sales hit 10-year high in Q4",
        "source": "Mint",
    },
    {
        "title": "Festive season e-commerce sales cross ₹1 lakh crore for first time",
        "source": "Business Standard",
    },
    {
        "title": "AI adoption among Indian SMEs doubles year-on-year",
        "source": "The Hindu BusinessLine",
    },
    {
        "title": "Bengaluru metro Phase 3 gets cabinet approval — commute times to drop 40%",
        "source": "Deccan Herald",
    },
]


def get_mock_tasks(fmt: str = "full") -> list[dict]:
    return MOCK_TASKS[:3] if fmt == "short" else MOCK_TASKS


def get_mock_meetings(fmt: str = "full") -> list[dict]:
    return MOCK_MEETINGS[:2] if fmt == "short" else MOCK_MEETINGS


def get_mock_news(fmt: str = "full") -> list[dict]:
    return MOCK_NEWS[:3] if fmt == "short" else MOCK_NEWS
