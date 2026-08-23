"""Знижки й акції на художні матеріали в українських магазинах.

Магазини змінюють верстку, тому парсер навмисно «широкий»: він не знає нічого
про класи конкретного сайту. Логіка така — беремо кожне посилання на товар
і піднімаємось на кілька рівнів вгору, шукаючи поруч ознаку знижки:
або бейдж «-XX%», або дві різні ціни (стара і нова).

Магазин недоступний, віддає JS-заглушку або змінив розмітку → просто
пропускаємо його, публікація не зривається.
"""
import html
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..config import DEALS_SOURCES
from ..filters import is_blocked

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "uk-UA,uk;q=0.9",
}

PRICE_RX = re.compile(
    r"(\d[\d\s  ]*(?:[.,]\d{2})?)\s*(?:грн|₴|uah)", re.I)
PERCENT_RX = re.compile(r"[-−–]\s?(\d{1,2})\s?%")
SKIP_HREF = re.compile(
    r"(^#|^javascript:|^mailto:|/login|/cart|/compare|/wishlist|/user/|/search)", re.I)
# Службові написи в картці товару — це не назва товару.
SKIP_NAME = re.compile(
    r"^(відгук|отзыв|порівн|сравн|купити|купить|в кошик|в корзин|детальніше|"
    r"подробнее|переглянути|дивитися|показати|ще |наявн|очікує|під замовл|"
    r"додати|избранное|обране|\d[\d\s.,()]*$)", re.I)
MAX_LEVELS = 5          # наскільки високо піднімаємось від посилання
MAX_NODE_TEXT = 900     # довший текст — це вже не картка товару, а вся сторінка


def _num(raw: str) -> int | None:
    """«2 340,00 ₴» -> 2340. Копійки відкидаємо, роздільники тисяч — теж."""
    raw = re.sub(r"[\s  ]", "", raw or "")
    raw = re.sub(r"[.,]\d{2}$", "", raw)
    digits = re.sub(r"\D", "", raw)
    return int(digits) if digits else None


def _name_of(link) -> str:
    img = link.find("img")
    # спершу видимий текст — він українською; data-name часто лишається
    # російським від старої версії каталогу
    for raw in (link.get_text(" ", strip=True), link.get("title"),
                img.get("alt") if img else None, link.get("aria-label"),
                link.get("data-name")):
        name = re.sub(r"\s+", " ", (raw or "")).strip()
        if len(name) >= 8:
            return name[:90]
    return ""


def _deal_from(text: str) -> str:
    """Ознака знижки в тексті картки: бейдж -XX% або пара «стара → нова ціна»."""
    percent = PERCENT_RX.search(text)
    if percent and 3 <= int(percent.group(1)) <= 95:
        return f"−{percent.group(1)}%"
    prices = [_num(p) for p in PRICE_RX.findall(text)]
    prices = [p for p in prices if p and 10 <= p <= 200000]
    if len(prices) >= 2 and prices[0] > prices[1]:
        return f"{prices[0]} → {prices[1]} грн"
    return ""


def _card_key(node) -> str:
    """Ключ картки товару: текст найбільшого предка, який ще схожий на картку.

    Потрібно, щоб посилання-картинка, посилання-назва й посилання-категорія
    з однієї картки не перетворилися на три «різні» знижки.
    """
    best = node
    parent = node.parent
    for _ in range(MAX_LEVELS):
        if parent is None:
            break
        text = re.sub(r"\s+", " ", parent.get_text(" ", strip=True))
        if len(text) > MAX_NODE_TEXT:
            break
        best, parent = parent, parent.parent
    return re.sub(r"\s+", " ", best.get_text(" ", strip=True))[:300]


def _shop_items(src: dict, limit: int = 4) -> list[dict]:
    html_text = ""
    for url in (src["url"], src["home"]):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        except Exception:
            continue
        if r.status_code < 400 and len(r.text) > 2000:
            html_text = r.text
            break
    if not html_text:
        return []

    soup = BeautifulSoup(html_text, "html.parser")
    items, seen_href, seen_name, seen_cards = [], set(), set(), set()

    for link in soup.find_all("a", href=True, limit=4000):
        raw_href = link["href"].strip()
        if not raw_href or SKIP_HREF.search(raw_href):
            continue
        href = urljoin(src["home"], raw_href)
        if not href.startswith("http") or href in seen_href:
            continue
        name = _name_of(link)
        if len(name) < 8 or name.lower() in seen_name or SKIP_NAME.match(name):
            continue

        deal, card = "", ""
        node = link
        for _ in range(MAX_LEVELS):
            node = node.parent
            if node is None:
                break
            text = re.sub(r"\s+", " ", node.get_text(" ", strip=True))
            if len(text) > MAX_NODE_TEXT:
                break
            deal = _deal_from(text)
            if deal:
                card = _card_key(node)
                break
        if not deal or is_blocked(name, href):
            continue
        # одна позиція з картки: «Відгуки», «Порівняти» тощо лежать поруч
        if card in seen_cards:
            continue
        seen_cards.add(card)

        seen_href.add(href)
        seen_name.add(name.lower())
        items.append({"name": name, "url": href, "deal": deal})
        if len(items) >= limit:
            break
    return items


def fetch(state: dict) -> dict | None:
    blocks = []
    for src in DEALS_SOURCES:
        try:
            found = _shop_items(src)
        except Exception:
            found = []
        if not found:
            continue
        lines = [f"<b>{html.escape(src['name'])}</b>"]
        for it in found[:3]:
            deal = f" — <i>{html.escape(it['deal'])}</i>" if it["deal"] else ""
            lines.append(
                f"• <a href=\"{html.escape(it['url'])}\">{html.escape(it['name'])}</a>{deal}")
        blocks.append("\n".join(lines))
        if len(blocks) >= 3:
            break

    if not blocks:
        return None

    text = ("🎨 <b>Знижки на художні матеріали</b>\n\n"
            + "\n\n".join(blocks)
            + "\n\n<i>Ціни змінюються — перевіряйте на сайті магазину.</i>\n#знижки #матеріали")
    return {"id": "deals:auto", "type": "deals", "text": text, "preview": False}
