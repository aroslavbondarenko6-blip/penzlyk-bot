# -*- coding: utf-8 -*-
"""Крон у воркфлоу має накривати вікна всіх слотів — і взимку, і влітку.

GitHub губить частину крон-подій, тому єдина гарантія — щоб у кожній годині
вікна слота планувалося кілька спроб. Цей тест ловить ситуацію, коли хтось
відредагував SLOTS або крон і вікно лишилося без жодного запуску.
"""
import re
import unittest
from pathlib import Path

from bot.config import SLOTS
from bot.main import slot_window

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "post.yml"
KYIV_OFFSETS = (2, 3)          # UTC+2 узимку, UTC+3 улітку
MIN_ATTEMPTS_PER_HOUR = 2      # менше — і одна загублена подія лишає діру


def _crons() -> list[str]:
    text = WORKFLOW.read_text(encoding="utf-8")
    return re.findall(r'-\s+cron:\s*"([^"]+)"', text)


def _expand(field: str, lo: int, hi: int) -> set[int]:
    """Розкрити одне поле крона у множину значень."""
    values: set[int] = set()
    for part in field.split(","):
        step = 1
        if "/" in part:
            part, raw_step = part.split("/", 1)
            step = int(raw_step)
        if part in ("*", ""):
            start, end = lo, hi
        elif "-" in part:
            start, end = (int(x) for x in part.split("-", 1))
        else:
            start = end = int(part)
        values.update(range(start, end + 1, step))
    return values


def _attempts_per_hour() -> dict[int, int]:
    """Скільки запусків заплановано в кожній годині UTC."""
    per_hour = {h: 0 for h in range(24)}
    for cron in _crons():
        minute, hour = cron.split()[0], cron.split()[1]
        minutes = _expand(minute, 0, 59)
        for h in _expand(hour, 0, 23):
            per_hour[h] += len(minutes)
    return per_hour


class TestCronCoversSlots(unittest.TestCase):
    def test_crons_parse(self):
        self.assertTrue(_crons(), "у post.yml немає жодного крона")

    def test_every_slot_window_is_covered(self):
        per_hour = _attempts_per_hour()
        for offset in KYIV_OFFSETS:
            for slot in SLOTS:
                open_at, close_at = slot_window(slot)
                start, end = open_at - offset * 60, close_at - offset * 60
                for minute in range(start, end + 1, 60):
                    hour = (minute // 60) % 24
                    with self.subTest(offset=offset, slot=slot, hour=hour):
                        self.assertGreaterEqual(
                            per_hour[hour], MIN_ATTEMPTS_PER_HOUR,
                            f"слот {slot}:00 Київ (UTC+{offset}): о {hour}:00 UTC "
                            f"заплановано лише {per_hour[hour]} спроб")

    def test_daily_heartbeat_exists(self):
        """Має бути крон, що працює цілодобово: він закриває прострочені слоти
        і не дає GitHub вимкнути розклад через 60 днів тиші."""
        all_day = [c for c in _crons() if c.split()[1] == "*"]
        self.assertTrue(all_day, "немає цілодобового крона-пульсу")

    def test_not_wasteful(self):
        """Розклад не має перетворюватись на тисячі запусків на добу."""
        total = sum(_attempts_per_hour().values())
        self.assertLess(total, 300, f"забагато запусків на добу: {total}")


if __name__ == "__main__":
    unittest.main()
