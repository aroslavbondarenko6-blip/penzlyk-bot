"""Свіжі новини артсвіту з українськомовних джерел."""
import html
import re
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from ..config import ART_KEYWORDS, NEWS_SOURCES
from ..filters import is_blocked

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; art-tg-autopost/1.0)"}
MAX_AGE_DAYS = 5


def _discover_feed(site: str) -> list[str]:
    """Знайти RSS на сторінці сайту, якщо прямий фід не спрацював."""
    try:
        r = requests.get(site, headers=HEADERS, timeout=25)
        found = re.findall(
            r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*>', r.text, re.I)
        urls = []
        for tag in found:
            m = re.search(r'href=["\']([^"\']+)["\']', tag, re.I)
            if m:
                href = html.unescape(m.group(1))
                if href.startswith("/"):
                    href = site.rstrip("/") + href
                urls.append(href)
        return urls[:3]
    except Exception:
        return []


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _is_art(title: str, summary: str) -> bool:
    blob = f"{title} {summary}".lower()
    return any(k in blob for k in ART_KEYWORDS)


def fetch(state: dict) -> dict | None:
    seen = state.get("seen_urls", {})
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    candidates = []

    for src in NEWS_SOURCES:
        feeds = list(src.get("feeds", []))
        parsed = None
        for url in feeds:
            try:
                d = feedparser.parse(url, request_headers=HEADERS)
                if d.entries:
                    parsed = d
                    break
            except Exception:
                continue
        if parsed is None:
            for url in _discover_feed(src["site"]):
                try:
                    d = feedparser.parse(url, request_headers=HEADERS)
                    if d.entries:
                        parsed = d
                        break
                except Exception:
                    continue
        if parsed is None:
            continue

        for entry in parsed.entries[:30]:
            link = (entry.get("link") or "").split("?")[0]
            title = _clean(entry.get("title", ""))
            summary = _clean(entry.get("summary", ""))[:400]
            if not link or not title or link in seen:
                continue
            if is_blocked(title, summary, link):
                continue
            if not _is_art(title, summary):
                continue
            published = None
            for key in ("published_parsed", "updated_parsed"):
                if entry.get(key):
                    published = datetime(*entry[key][:6], tzinfo=timezone.utc)
                    break
            if published and published < cutoff:
                continue
            candidates.append({
                "source": src["name"], "title": title,
                "summary": summary, "link": link,
                "published": published or datetime.now(timezone.utc),
            })

    if not candidates:
        return None
    candidates.sort(key=lambda c: c["published"], reverse=True)
    best = candidates[0]

    summary = best["summary"]
    if len(summary) > 320:
        summary = summary[:317].rsplit(" ", 1)[0] + "…"

    text = (f"📰 <b>{html.escape(best['title'])}</b>\n\n"
            f"{html.escape(summary)}\n\n"
            f"<a href=\"{html.escape(best['link'])}\">Читати на {html.escape(best['source'])}</a>\n\n"
            f"#новини #мистецтво")
    return {"id": f"news:{best['link']}", "type": "news", "text": text,
            "url": best["link"], "preview": True}
