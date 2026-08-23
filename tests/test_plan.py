# -*- coding: utf-8 -*-
"""План контенту по слотах і фолбеки, коли джерело мовчить."""
import unittest
from datetime import datetime
from unittest import mock

from bot import main as bot_main
from bot.config import TZ


def day(y, m, d, hh=15):
    return datetime(y, m, d, hh, 0, tzinfo=TZ)


class TestBuildPost(unittest.TestCase):
    def setUp(self):
        self.state = {"used_ids": {}, "seen_urls": {}}

    def _run(self, slot, now, news=None, deals=None, evergreen=None):
        with mock.patch.object(bot_main.news, "fetch", side_effect=news or (lambda st: None)), \
             mock.patch.object(bot_main.deals, "fetch", side_effect=deals or (lambda st: None)), \
             mock.patch.object(bot_main.evergreen, "pick",
                               side_effect=evergreen or (lambda kind, st: None)):
            return bot_main.build_post(slot, now, self.state)

    def test_10_prefers_news(self):
        item = self._run(10, day(2026, 8, 23, 10),
                         news=lambda st: {"id": "news:x", "type": "news", "text": "новина"},
                         evergreen=lambda kind, st: {"id": kind, "type": kind, "text": kind})
        self.assertEqual(item["type"], "news")

    def test_10_falls_back_to_fact_then_artwork(self):
        """Падіння RSS не має зривати публікацію."""
        item = self._run(10, day(2026, 8, 23, 10),
                         evergreen=lambda kind, st: {"id": kind, "type": kind, "text": kind}
                         if kind == "fact" else None)
        self.assertEqual(item["type"], "fact")

    def test_provider_exception_does_not_break_post(self):
        def boom(st):
            raise RuntimeError("RSS впав")
        item = self._run(10, day(2026, 8, 23, 10), news=boom,
                         evergreen=lambda kind, st: {"id": kind, "type": kind, "text": kind})
        self.assertEqual(item["type"], "fact")

    def test_15_tuesday_prefers_deals(self):
        item = self._run(15, day(2026, 8, 25),          # вівторок
                         deals=lambda st: {"id": "deals:auto", "type": "deals", "text": "знижки"},
                         evergreen=lambda kind, st: {"id": kind, "type": kind, "text": kind})
        self.assertEqual(item["type"], "deals")

    def test_15_friday_prefers_deals(self):
        item = self._run(15, day(2026, 8, 28),          # п'ятниця
                         deals=lambda st: {"id": "deals:auto", "type": "deals", "text": "знижки"},
                         evergreen=lambda kind, st: {"id": kind, "type": kind, "text": kind})
        self.assertEqual(item["type"], "deals")

    def test_15_tuesday_without_deals_falls_back_to_artwork(self):
        item = self._run(15, day(2026, 8, 25),
                         evergreen=lambda kind, st: {"id": kind, "type": kind, "text": kind})
        self.assertEqual(item["type"], "artwork")

    def test_15_sunday_is_artwork(self):
        item = self._run(15, day(2026, 8, 23),          # неділя
                         deals=lambda st: {"id": "deals:auto", "type": "deals", "text": "знижки"},
                         evergreen=lambda kind, st: {"id": kind, "type": kind, "text": kind})
        self.assertEqual(item["type"], "artwork")

    def test_20_is_meme(self):
        item = self._run(20, day(2026, 8, 23, 20),
                         evergreen=lambda kind, st: {"id": kind, "type": kind, "text": kind})
        self.assertEqual(item["type"], "meme")

    def test_nothing_available(self):
        self.assertIsNone(self._run(20, day(2026, 8, 23, 20)))


if __name__ == "__main__":
    unittest.main()
