"""Знижки й акції на художні матеріали в українських магазинах.

Магазини змінюють верстку, тому парсер навмисно «широкий»: шукає товари зі
старою й новою ціною або зі знаком «-XX%». Якщо магазин недоступний або
розмітка змінилась — просто пропускаємо його, пост не зривається.
"""
import html
import re

import requests
from bs4 import BeautifulSoup

from ..config import DEALS_SOURCES
from ..filters import is_blocked

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; art-tg-autopost/1.0)",
           "Accept-Language": "uk-UA,uk;q=0.9"}

PRICE_RX = re.compile(r"(\d[\d\s  ]{1,9})\s*(?:грн|₴|uah)", re.I)
PERCENT_RX = re.compile(r"-\s?(\d{1,2})\s?%")


def _shop_items(src: dict, limit: int = 4) -> list[dict]:
    try:
        r = requests.get(src["url"], headers=HEADERS, timeout=30)
        if r.status_code >= 400:
            r = requests.get(src["home"], headers=HEADERS, timeout=30)
        if r.status_code >= 400:
            return []
    except Exception:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    items, seen = [], set()

    for node in soup.find_all(["li", "div", "article"], limit=1200):
        text = re.sub(r"\s+", " ", node.get_text(" ", strip=True))
        if not (25 < len(text) < 220):
            continue
        prices = PRICE_RX.findall(text)
        percent = PERCENT_RX.search(text)
        if not (len(prices) >= 2 or percent):
            continue
        link = node.find("a", href=True)
        if not link:
            continue
        href = link["href"]
        if href.startswith("/"):
            href = src["home"].rstrip("/") + href
        if not href.startswith("http") or href in seen:
            continue
        name = re.sub(r"\s+", " ", link.get_text(" ", strip=True))[:90]
        if len(name) < 6 or is_blocked(name, href):
            continue
        seen.add(href)
        deal = ""
        if percent:
            deal = f"−{percent.group(1)}%"
        elif len(prices) >= 2:
            old = prices[0].strip().replace(" ", "")
            new = prices[1].strip().replace(" ", "")
            deal = f"{old} → {new} грн"
        items.append({"name": name, "url": href, "deal": deal})
        if len(items) >= limit:
            break
    return items


def fetch(state: dict) -> dict | None:
    blocks = []
    for src in DEALS_SOURCES:
        found = _shop_items(src)
        if not found:
            continue
        lines = [f"<b>{html.escape(src['name'])}</b>"]
        for it in found[:3]:
            deal = f" — <i>{html.escape(it['deal'])}</i>" if it["deal"] else ""
            lines.append(f"• <a href=\"{html.escape(it['url'])}\">{html.escape(it['name'])}</a>{deal}")
        blocks.append("\n".join(lines))
        if len(blocks) >= 3:
            break

    if not blocks:
        return None

    text = ("🎨 <b>Знижки на художні матеріали</b>\n\n"
            + "\n\n".join(blocks)
            + "\n\n<i>Ціни змінюються — перевіряйте на сайті магазину.</i>\n#знижки #матеріали")
    return {"id": "deals:auto", "type": "deals", "text": text, "preview": False}
