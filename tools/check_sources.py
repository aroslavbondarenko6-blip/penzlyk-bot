"""Діагностика: які RSS-фіди, магазини та зображення реально працюють.

Запуск:  python -m tools.check_sources          — усе
         python -m tools.check_sources --fast   — без перевірки картинок
"""
import json
import sys
import time
from pathlib import Path

import feedparser
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import DEALS_SOURCES, NEWS_SOURCES          # noqa: E402
from bot.providers import artwork, deals, news               # noqa: E402

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; art-tg-autopost/1.0)"}
FAST = "--fast" in sys.argv
problems: list[str] = []

print("=== RSS-джерела новин ===")
for src in NEWS_SOURCES:
    ok = None
    for url in src["feeds"]:
        try:
            d = feedparser.parse(url, request_headers=HEADERS)
            if d.entries:
                ok = f"{url} ({len(d.entries)} записів)"
                break
        except Exception:
            pass
    if not ok:
        found = news._discover_feed(src["site"])
        for url in found:
            try:
                d = feedparser.parse(url, request_headers=HEADERS)
                if d.entries:
                    ok = f"автопошук: {url} ({len(d.entries)} записів)"
                    break
            except Exception:
                pass
    print(f"  {'OK  ' if ok else 'FAIL'} {src['name']}: {ok or 'фід не відповідає'}")
    if not ok:
        problems.append(f"news:{src['name']}")

print("\n=== Магазини (знижки) ===")
for src in DEALS_SOURCES:
    try:
        items = deals._shop_items(src)
    except Exception as exc:
        items = []
        print(f"       (виняток: {exc})")
    print(f"  {'OK  ' if items else 'FAIL'} {src['name']}: знайдено {len(items)} позицій")
    if not items:
        problems.append(f"deals:{src['name']}")

if not FAST:
    print("\n=== Зображення до «картини дня» ===")
    bank = json.loads((Path(__file__).resolve().parent.parent / "content" / "evergreen.json")
                      .read_text(encoding="utf-8"))
    for item in [i for i in bank if i["type"] == "artwork"]:
        url = artwork.image_url(item["wiki"], item.get("lang", "en"))
        status = ""
        if url:
            try:
                r = requests.head(url, headers=HEADERS, timeout=25, allow_redirects=True)
                status = str(r.status_code)
            except Exception as exc:
                status = f"err {exc}"
        good = bool(url) and status.startswith("2")
        print(f"  {'OK  ' if good else 'FAIL'} {item['id']} {item['wiki']} -> {status or 'немає файлу'}")
        if not good:
            problems.append(f"image:{item['id']}")
        time.sleep(1.2)   # Вікімедіа лімітує API: без паузи прилітає 429

print("\n=== Підсумок ===")
if problems:
    print(f"Проблемні джерела ({len(problems)}): " + ", ".join(problems))
    print("Це не критично: бот автоматично підставляє запасний тип контенту.")
else:
    print("Усі джерела працюють.")
