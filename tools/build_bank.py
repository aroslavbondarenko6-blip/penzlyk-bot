# -*- coding: utf-8 -*-
"""Збирає content/evergreen.json із текстових блоків."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from build_bank_1 import FACTS
from build_bank_2 import ARTWORKS, MEMES
from bot.filters import is_blocked, reason

items = []
for n, (text, tags) in enumerate(FACTS, 1):
    items.append({"id": f"fact-{n:03d}", "type": "fact", "text": f"💡 {text}\n\n{tags}"})
for n, (text, tags) in enumerate(MEMES, 1):
    items.append({"id": f"meme-{n:03d}", "type": "meme", "text": f"😄 {text}\n\n{tags}"})
for n, (wiki, lang, text, tags) in enumerate(ARTWORKS, 1):
    items.append({"id": f"art-{n:03d}", "type": "artwork", "wiki": wiki,
                  "lang": lang, "text": f"{text}\n\n{tags}"})

bad = [i for i in items if is_blocked(i["text"], i.get("wiki", ""))]
if bad:
    for i in bad:
        print("BLOCKED:", i["id"], reason(i["text"], i.get("wiki", "")))
    raise SystemExit("Знайдено росконтент у банку — виправте перед збіркою")

too_long = [i for i in items if i["type"] == "artwork" and len(i["text"]) > 1024]
if too_long:
    raise SystemExit(f"Занадто довгі підписи до фото: {[i['id'] for i in too_long]}")

out = Path(__file__).parent.parent / "content" / "evergreen.json"
out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Записано {len(items)} елементів у {out}")
from collections import Counter
print(Counter(i["type"] for i in items))
