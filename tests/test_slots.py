# -*- coding: utf-8 -*-
"""Тести логіки слотів: коли постити, а коли тихо закрити прострочений слот."""
import unittest
from datetime import datetime

from bot.config import SLOT_GAP_MINUTES, SLOT_GRACE_MINUTES, SLOTS, TZ
from bot.main import due_slot, slot_window


def at(hh: int, mm: int) -> datetime:
    """Київський час 23 серпня 2026 (неділя)."""
    return datetime(2026, 8, 23, hh, mm, tzinfo=TZ)


class TestDueSlot(unittest.TestCase):
    def test_before_first_slot(self):
        done = []
        self.assertIsNone(due_slot(at(9, 59), done))
        self.assertEqual(done, [], "нічого не має закриватись до 10:00")

    def test_exactly_at_slot(self):
        self.assertEqual(due_slot(at(10, 0), []), 10)

    def test_inside_window(self):
        for hh, mm in ((10, 30), (12, 29), (12, 31), (14, 0), (14, 30)):
            with self.subTest(time=f"{hh}:{mm:02d}"):
                self.assertEqual(due_slot(at(hh, mm), []), 10)

    def test_windows(self):
        """Слот живе до наступного (мінус буфер), останній — SLOT_GRACE_MINUTES."""
        self.assertEqual(slot_window(10), (10 * 60, 15 * 60 - SLOT_GAP_MINUTES))   # 10:00-14:30
        self.assertEqual(slot_window(15), (15 * 60, 20 * 60 - SLOT_GAP_MINUTES))   # 15:00-19:30
        self.assertEqual(slot_window(20), (20 * 60, 20 * 60 + SLOT_GRACE_MINUTES))  # 20:00-22:30

    def test_expired_slot_closes_silently(self):
        done = []
        self.assertIsNone(due_slot(at(14, 31), done),
                          "прострочений слот не має публікуватись")
        self.assertIn(10, done, "прострочений слот має бути закритий у стані")

    def test_gap_between_slots_is_quiet(self):
        """Між 14:31 і 15:00 не публікуємо нічого: щоб два пости не злиплися."""
        self.assertIsNone(due_slot(at(14, 45), []))

    def test_evening_slot_never_runs_late(self):
        self.assertEqual(due_slot(at(22, 30), []), 20)
        done = []
        self.assertIsNone(due_slot(at(22, 31), done),
                          "після 22:30 вечірній пост уже не виходить")
        self.assertIn(20, done)

    def test_evening_slot(self):
        done = []
        self.assertEqual(due_slot(at(20, 10), done), 20)
        self.assertIn(10, done)
        self.assertIn(15, done)

    def test_night_nothing_fires(self):
        done = []
        self.assertIsNone(due_slot(at(3, 0), done),
                          "о 3-й ночі вечірній пост не має прилітати")

    def test_after_evening_grace(self):
        done = []
        self.assertIsNone(due_slot(at(23, 0), done))
        self.assertEqual(done, sorted(SLOTS))

    def test_already_published_slot_skipped(self):
        self.assertIsNone(due_slot(at(10, 30), [10]))
        self.assertEqual(due_slot(at(15, 5), [10]), 15)

    def test_grace_value(self):
        self.assertEqual(SLOT_GRACE_MINUTES, 150)


class TestDealsDay(unittest.TestCase):
    def test_tuesday_and_friday(self):
        from bot.config import DEALS_WEEKDAYS
        self.assertEqual(DEALS_WEEKDAYS, {1, 4})
        self.assertEqual(datetime(2026, 8, 25).weekday(), 1)  # вівторок
        self.assertEqual(datetime(2026, 8, 28).weekday(), 4)  # п'ятниця


if __name__ == "__main__":
    unittest.main()
