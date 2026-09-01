"""Діагностика: які магазини та зображення реально працюють.

Запуск:  python -m tools.check_sources               — магазини, вибірка картин
         python -m tools.check_sources --fast        — без картинок узагалі
         python -m tools.check_sources --all-images  — перевірити всі картини
             (довго: Вікімедіа лімітує API, між запитами тримаємо паузу)
"""
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import DEALS_SOURCES                        # noqa: E402
from bot.providers import artwork, deals                    # noqa: E402

HEADERS = {
    # Частина сайтів відрізає «ботоподібні» UA — прикидаємось браузером.
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "uk-UA,uk;q=0.9,en;q=0.5",
}
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


print("=== Магазини (знижки) ===")
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
