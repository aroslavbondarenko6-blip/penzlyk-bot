# -*- coding: utf-8 -*-
"""Тести логіки слотів: коли постити, а коли тихо закрити прострочений слот."""
import unittest
from datetime import datetime

from bot.config import SLOT_GRACE_MINUTES, SLOTS, TZ
from bot.main import due_slot


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

    def test_inside_grace(self):
        self.assertEqual(due_slot(at(12, 29), []), 10)
        self.assertEqual(due_slot(at(12, 30), []), 10)

    def test_expired_slot_closes_silently(self):
        done = []
        self.assertIsNone(due_slot(at(12, 31), done),
                          "прострочений слот не має публікуватись")
        self.assertIn(10, done, "прострочений слот має бути закритий у стані")

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
