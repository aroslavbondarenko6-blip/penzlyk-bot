"""Точка входу: вирішує, чи час постити, обирає контент і публікує."""
import argparse
import sys
import traceback
from datetime import datetime

from . import state as state_mod
from . import telegram
from .config import DEALS_WEEKDAYS, SLOTS, SLOT_GRACE_MINUTES, SLOT_PLAN, TZ
from .filters import is_blocked, reason
from .providers import artwork, deals, evergreen, news


def due_slot(now: datetime, done_today: list[int]) -> int | None:
    minutes = now.hour * 60 + now.minute
    for slot in sorted(SLOTS):
        if slot in done_today:
            continue
        start = slot * 60
        if start <= minutes <= start + SLOT_GRACE_MINUTES:
            return slot
        if minutes > start + SLOT_GRACE_MINUTES:
            done_today.append(slot)  # прострочено — тихо закриваємо слот
    return None


def build_post(slot: int, now: datetime, st: dict) -> dict | None:
    plan = list(SLOT_PLAN.get(slot, ["fact"]))
    if slot == 15 and now.weekday() in DEALS_WEEKDAYS:
        plan.insert(0, "deals")

    for kind in plan:
        try:
            if kind == "news":
                item = news.fetch(st)
            elif kind == "deals":
                item = deals.fetch(st)
            else:
                item = evergreen.pick(kind, st)
        except Exception:
            traceback.print_exc()
            item = None
        if item:
            print(f"[plan] слот {slot}: обрано тип '{kind}' ({item['id']})")
            return item
        print(f"[plan] слот {slot}: тип '{kind}' порожній, пробую далі")
    return None


def publish(item: dict, dry_run: bool = False) -> None:
    """Перша перевірка фільтром — тут; друга — у telegram._call перед відправкою."""
    text = item["text"]
    if is_blocked(text, item.get("wiki", ""), item.get("url", "")):
        raise RuntimeError(f"Пост заблоковано фільтром: {reason(text)}")

    photo = None
    if item.get("wiki"):
        photo = artwork.image_url(item["wiki"], item.get("lang", "en"))
    elif item.get("commons"):
        photo = artwork.commons_url(item["commons"])

    if dry_run:
        print("--- DRY RUN ---")
        print("type:", item.get("type"), "| id:", item["id"])
        print("photo:", photo or "(без фото, піде текстом)")
        print("len:", len(text))
        print(text)
        return

    if photo and len(text) <= telegram.CAPTION_LIMIT:
        try:
            telegram.send_photo(photo, text)
            return
        except Exception as exc:
            print(f"[warn] sendPhoto не вдався ({exc}) — надсилаю текстом")
    telegram.send_message(text, preview=item.get("preview", True))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-slot", type=int, help="запостити конкретний слот негайно")
    ap.add_argument("--dry-run", action="store_true", help="показати пост, але не надсилати")
    args = ap.parse_args()

    st = state_mod.load()
    now = datetime.now(TZ)
    today = now.date().isoformat()
    done_today = list(st["done_slots"].get(today, []))

    slot = args.force_slot if args.force_slot else due_slot(now, done_today)
    st["done_slots"][today] = sorted(set(done_today))

    if slot is None:
        print(f"[skip] {now:%Y-%m-%d %H:%M} Київ — жодного слоту не настало")
        state_mod.save(st)
        return 0

    item = build_post(slot, now, st)
    if item is None:
        print("[error] не вдалося зібрати пост із жодного джерела")
        st["last_error"] = f"{today} слот {slot}: немає контенту"
        state_mod.save(st)
        return 1

    try:
        publish(item, dry_run=args.dry_run)
    except Exception as exc:
        traceback.print_exc()
        st["last_error"] = f"{today} слот {slot}: {exc}"
        state_mod.save(st)
        return 1

    if not args.dry_run:
        st["done_slots"].setdefault(today, [])
        st["done_slots"][today] = sorted(set(st["done_slots"][today] + [slot]))
        if item["id"].startswith("news:"):
            st["seen_urls"][item["url"]] = today
        elif not item["id"].startswith("deals:"):
            st["used_ids"][item["id"]] = today
        st["last_error"] = None
        state_mod.save(st)
        print(f"[ok] опубліковано слот {slot} ({item['id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
