import os
from flagsmith import Flagsmith
from flagsmith.models import DefaultFlag

# Multivariate flag for A/B experiment: "short" vs "full" briefing
# Set this up in Flagsmith as a multivariate String flag with:
#   Control: "full" (50%)
#   Variant:  "short" (50%)
# Conversion event: "briefing_delivered"

_DEFAULT_TOPICS = "AI,Apple HomeKit,Apple,Matter home automation,India real estate"

_DEFAULTS: dict[str, DefaultFlag] = {
    "user_language":    DefaultFlag(True, "en-IN"),
    "show_tasks":       DefaultFlag(True, None),
    "show_meetings":    DefaultFlag(True, None),
    "show_news":        DefaultFlag(True, None),
    "briefing_format":  DefaultFlag(True, "full"),
    "news_topics":      DefaultFlag(True, _DEFAULT_TOPICS),
}

_client: Flagsmith | None = None


def _get_client() -> Flagsmith:
    global _client
    if _client is None:
        _client = Flagsmith(
            environment_key=os.environ["FLAGSMITH_ENVIRONMENT_KEY"],
            enable_events=True,
            default_flag_handler=lambda name: _DEFAULTS.get(
                name, DefaultFlag(False, None)
            ),
        )
    return _client


def get_user_flags(user_id: str) -> dict:
    client = _get_client()

    # A/B experiment — records exposure automatically
    fmt_flag = client.get_experiment_flag("briefing_format", identifier=user_id)

    identity_flags = client.get_identity_flags(user_id)

    return {
        "language": str(
            identity_flags.get_flag("user_language").value or "en-IN"
        ),
        "show_tasks": bool(identity_flags.get_flag("show_tasks").enabled),
        "show_meetings": bool(identity_flags.get_flag("show_meetings").enabled),
        "show_news": bool(identity_flags.get_flag("show_news").enabled),
        "briefing_format": str(fmt_flag.value or "full"),
        "news_topics": [
            t.strip()
            for t in str(
                identity_flags.get_flag("news_topics").value or _DEFAULT_TOPICS
            ).split(",")
            if t.strip()
        ],
    }


def track_delivered(user_id: str) -> None:
    _get_client().track_event("briefing_delivered", identifier=user_id)
