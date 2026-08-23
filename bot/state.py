"""Стан публікацій: що і коли вже пішло в групу."""
import json
import os
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "state" / "state.json"

DEFAULT = {
    "done_slots": {},      # "2026-08-23": [10, 15]
    "used_ids": {},        # "fact-001": "2026-08-23"
    "seen_urls": {},       # url -> дата
    "last_error": None,
}


def load() -> dict:
    if STATE_PATH.exists():
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            return {**DEFAULT, **data}
        except json.JSONDecodeError:
            pass
    return json.loads(json.dumps(DEFAULT))


def save(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # тримаємо файл компактним: історія за останні 120 днів
    state["done_slots"] = dict(sorted(state["done_slots"].items())[-120:])
    state["seen_urls"] = dict(sorted(state["seen_urls"].items(), key=lambda kv: kv[1])[-800:])
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
