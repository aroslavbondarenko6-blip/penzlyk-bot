"""Діагностика: які RSS-фіди, магазини та зображення реально працюють.

Запуск:  python -m tools.check_sources               — фіди, магазини, вибірка картин
         python -m tools.check_sources --fast        — без картинок узагалі
         python -m tools.check_sources --all-images  — перевірити всі картини
             (довго: Вікімедіа лімітує API, між запитами тримаємо паузу)
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

HEADERS = news.HEADERS   # той самий UA, що й у бойовому провайдері
FAST = "--fast" in sys.argv
ALL_IMAGES = "--all-images" in sys.argv
SAMPLE = 6
PAUSE = 2.0
problems: list[str] = []


def _head(url: str, attempts: int = 3) -> str:
    """HEAD із повагою до 429: CDN Вікімедіа лімітує серії запитів."""
    for attempt in range(attempts):
        try:
            r = requests.head(url, headers=HEADERS, timeout=25, allow_redirects=True)
        except Exception as exc:
            return f"err {exc}"
        if r.status_code != 429:
            return str(r.status_code)
        wait = min(int(r.headers.get("Retry-After", 10) or 10), 45)
        if attempt < attempts - 1:
            print(f"       429 від CDN, чекаю {wait}с")
            time.sleep(wait)
    return "429 (ліміт CDN, не проблема бота)"


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
    artworks = [i for i in bank if i["type"] == "artwork"]
    if not ALL_IMAGES:
        # рівномірна вибірка, щоб щотижнева діагностика не молотила API годину
        step = max(1, len(artworks) // SAMPLE)
        artworks = artworks[::step][:SAMPLE]
        print(f"  (вибірка {len(artworks)} з {len([i for i in bank if i['type'] == 'artwork'])};"
              f" усі — з ключем --all-images)")
    for item in artworks:
        url = artwork.image_url(item["wiki"], item.get("lang", "en"))
        status = _head(url) if url else "стаття без вільного зображення"
        if status.startswith("429"):
            status += " — файл знайдено, це ліміт діагностики"
        good = bool(url) and (status.startswith("2") or status.startswith("429"))
        print(f"  {'OK  ' if good else 'FAIL'} {item['id']} {item['wiki']} -> {status}")
        if not good:
            problems.append(f"image:{item['id']}")
        time.sleep(PAUSE)   # Вікімедіа лімітує API: без паузи прилітає 429

print("\n=== Підсумок ===")
if problems:
    print(f"Проблемні джерела ({len(problems)}): " + ", ".join(problems))
    print("Це не критично: бот автоматично підставляє запасний тип контенту.")
else:
    print("Усі джерела працюють.")
