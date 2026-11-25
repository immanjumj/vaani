import os
import httpx
from briefing.mock_data import get_mock_news


async def get_news(fmt: str = "full") -> list[dict]:
    url = os.getenv("SCOUT_API_URL", "").strip()
    if not url:
        return get_mock_news(fmt)

    limit = 3 if fmt == "short" else 5
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params={"limit": limit})
            resp.raise_for_status()
            data = resp.json()
            # Scout may return {"articles": [...]} or a bare list
            articles = data.get("articles", data) if isinstance(data, dict) else data
            return [
                {"title": a.get("title", ""), "source": a.get("source", "")}
                for a in articles[:limit]
                if a.get("title")
            ]
    except Exception:
        return get_mock_news(fmt)
