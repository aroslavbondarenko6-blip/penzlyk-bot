"""Банк вічнозеленого контенту: факти, меми, картина дня."""
import json
import random
from pathlib import Path

from ..filters import is_blocked

BANK_PATH = Path(__file__).resolve().parent.parent.parent / "content" / "evergreen.json"


def _load() -> list[dict]:
    items = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    return [i for i in items if not is_blocked(i.get("text", ""), i.get("wiki", ""))]


def pick(kind: str, state: dict) -> dict | None:
    """Обрати невикористаний елемент потрібного типу. Коли банк вичерпано —
    цикл починається спочатку (найдавніше використане йде першим)."""
    items = [i for i in _load() if i.get("type") == kind]
    if not items:
        return None
    used = state.get("used_ids", {})
    fresh = [i for i in items if i["id"] not in used]
    if fresh:
        return random.choice(fresh)
    items.sort(key=lambda i: used.get(i["id"], ""))
    return items[0]
