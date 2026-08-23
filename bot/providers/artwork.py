"""Підбір зображення твору через Wikimedia (публічний домен / вільні ліцензії).

Ми ніколи не зберігаємо прямі URL картинок — вони протухають. У банку лежить
лише назва статті Вікіпедії, а посилання на файл беремо в рантаймі через
MediaWiki API (`prop=pageimages&piprop=original|thumbnail`).
"""
import time
from urllib.parse import urlsplit, urlunsplit

import requests

HEADERS = {"User-Agent": "art-tg-autopost/1.0 (Telegram art digest; "
                         "https://github.com/topics/telegram-bot)"}
# Вікімедіа віддає 429 з Retry-After, якщо смикати API надто часто.
RETRY_ON_429 = 2
MAX_WAIT = 40

# Telegram не приймає фото за URL, якщо файл > 10 МБ або сума сторін > 10000 px,
# тому оригінал беремо лише коли він явно в межах, інакше — мініатюру.
MAX_SIDE_SUM = 10000
THUMB_WIDTH = 1600
GOOD_EXT = (".jpg", ".jpeg", ".png")


def _strip_query(url: str) -> str:
    """Прибрати ?utm_source=… — API додає їх, і розширення файлу «зникає»."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _usable(info: dict | None) -> str | None:
    if not info or not info.get("source"):
        return None
    url = _strip_query(info["source"])
    if not url.lower().endswith(GOOD_EXT):
        return None
    w, h = info.get("width") or 0, info.get("height") or 0
    if w and h and w + h > MAX_SIDE_SUM:
        return None
    return url


def image_url(wiki_title: str, lang: str = "en") -> str | None:
    """Головне зображення статті Вікіпедії у розмірі, придатному для Telegram."""
    if not wiki_title:
        return None
    hosts = []
    for host in (f"https://{lang}.wikipedia.org", "https://uk.wikipedia.org",
                 "https://en.wikipedia.org"):
        if host not in hosts:
            hosts.append(host)

    for host in hosts:
        pages = _query(host, wiki_title)
        for page in pages.values():
            # мініатюра надійніша: оригінали музейних сканів бувають по 40 МБ
            url = _usable(page.get("thumbnail")) or _usable(page.get("original"))
            if url:
                return url
    return None


def _query(host: str, wiki_title: str) -> dict:
    """Один запит до MediaWiki API з повагою до Retry-After."""
    for attempt in range(RETRY_ON_429 + 1):
        try:
            r = requests.get(
                f"{host}/w/api.php",
                params={
                    "action": "query", "format": "json", "titles": wiki_title,
                    "prop": "pageimages", "piprop": "original|thumbnail",
                    "pithumbsize": THUMB_WIDTH, "redirects": 1,
                },
                headers=HEADERS, timeout=30,
            )
            if r.status_code == 429 and attempt < RETRY_ON_429:
                wait = min(int(r.headers.get("Retry-After", 5) or 5), MAX_WAIT)
                print(f"[wiki] 429 від {host}, чекаю {wait}с")
                time.sleep(wait)
                continue
            if r.status_code != 200:
                return {}
            return r.json().get("query", {}).get("pages", {})
        except Exception as exc:
            print(f"[wiki] {host}: {exc}")
            return {}
    return {}


def commons_url(filename: str, width: int = THUMB_WIDTH) -> str:
    """Прямий URL файлу з Wikimedia Commons."""
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}?width={width}"
