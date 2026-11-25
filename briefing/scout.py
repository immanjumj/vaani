import xml.etree.ElementTree as ET
from urllib.parse import quote

import httpx

_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


async def _fetch_topic(topic: str, limit: int) -> list[dict]:
    url = _GOOGLE_NEWS_RSS.format(q=quote(topic))
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(url, headers=_HEADERS)
        resp.raise_for_status()

    root = ET.fromstring(resp.text)
    articles = []
    for item in root.findall(".//item")[:limit]:
        title = item.findtext("title", "").strip()
        source_el = item.find("source")
        source = source_el.text.strip() if source_el is not None else ""
        # Google News appends " - Source Name" to titles — strip it
        if " - " in title:
            title = title.rsplit(" - ", 1)[0].strip()
        if title:
            articles.append({"title": title, "source": source, "topic": topic})
    return articles


async def get_news(topics: list[str], fmt: str = "full") -> list[dict]:
    per_topic = 1 if fmt == "short" else 2
    results = []
    for topic in topics:
        try:
            articles = await _fetch_topic(topic, per_topic)
            results.extend(articles)
        except Exception:
            pass
    return results
