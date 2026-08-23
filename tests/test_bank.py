# -*- coding: utf-8 -*-
"""Тести банку вічнозеленого контенту."""
import json
import re
import unittest
from collections import Counter
from pathlib import Path

from bot.filters import is_blocked, reason
from bot.telegram import CAPTION_LIMIT, MESSAGE_LIMIT

BANK_PATH = Path(__file__).resolve().parent.parent / "content" / "evergreen.json"
BANK = json.loads(BANK_PATH.read_text(encoding="utf-8"))

ALLOWED_TAGS = {"b", "i", "u", "s", "a", "code", "pre", "blockquote", "tg-spoiler"}


class TestBank(unittest.TestCase):
    def test_size(self):
        self.assertGreaterEqual(len(BANK), 100, "у банку має бути щонайменше 100 постів")

    def test_all_types_present(self):
        kinds = Counter(i["type"] for i in BANK)
        for kind in ("fact", "artwork", "meme"):
            self.assertGreater(kinds[kind], 0, f"немає жодного елемента типу {kind}")
        self.assertGreaterEqual(kinds["fact"], 40)
        self.assertGreaterEqual(kinds["artwork"], 35)
        self.assertGreaterEqual(kinds["meme"], 25)

    def test_unique_ids(self):
        ids = [i["id"] for i in BANK]
        dupes = [k for k, v in Counter(ids).items() if v > 1]
        self.assertEqual(dupes, [], f"дублікати id: {dupes}")

    def test_no_ros_content(self):
        bad = [(i["id"], reason(i["text"], i.get("wiki", "")))
               for i in BANK if is_blocked(i["text"], i.get("wiki", ""))]
        self.assertEqual(bad, [], f"росконтент у банку: {bad}")

    def test_caption_limit(self):
        """Підпис до фото в Telegram — максимум 1024 символи."""
        long = [(i["id"], len(i["text"])) for i in BANK
                if i["type"] == "artwork" and len(i["text"]) > CAPTION_LIMIT]
        self.assertEqual(long, [], f"задовгі підписи до фото: {long}")

    def test_message_limit(self):
        long = [(i["id"], len(i["text"])) for i in BANK if len(i["text"]) > MESSAGE_LIMIT]
        self.assertEqual(long, [], f"задовгі повідомлення: {long}")

    def test_artwork_has_wiki(self):
        for i in BANK:
            if i["type"] == "artwork":
                with self.subTest(id=i["id"]):
                    self.assertTrue(i.get("wiki"), "у artwork має бути поле wiki")
                    self.assertIn(i.get("lang"), ("uk", "en"))

    def test_html_tags_are_valid_for_telegram(self):
        for i in BANK:
            for tag in re.findall(r"</?([a-zA-Z-]+)", i["text"]):
                with self.subTest(id=i["id"], tag=tag):
                    self.assertIn(tag.lower(), ALLOWED_TAGS,
                                  f"{i['id']}: Telegram не знає тега <{tag}>")

    def test_html_tags_balanced(self):
        for i in BANK:
            for tag in ALLOWED_TAGS:
                opened = len(re.findall(rf"<{tag}(?:\s[^>]*)?>", i["text"]))
                closed = len(re.findall(rf"</{tag}>", i["text"]))
                with self.subTest(id=i["id"], tag=tag):
                    self.assertEqual(opened, closed, f"{i['id']}: незакритий <{tag}>")

    def test_text_is_ukrainian(self):
        """Кожен пост має містити кирилицю — банк українською."""
        for i in BANK:
            with self.subTest(id=i["id"]):
                self.assertRegex(i["text"], r"[а-яіїєґА-ЯІЇЄҐ]")

    def test_ukrainian_share_of_facts(self):
        """Приблизно третина фактів — про українське мистецтво."""
        facts = [i for i in BANK if i["type"] == "fact"]
        ua = [i for i in facts if "#україна" in i["text"]
              or any(k in i["text"].lower() for k in
                     ("примаченко", "білокур", "богомазов", "бойчук", "пінзел",
                      "горська", "марчук", "петриківськ", "софі", "малевич",
                      "куїндж", "рєпін", "айвазовськ", "київ", "україн"))]
        self.assertGreaterEqual(len(ua), len(facts) // 4,
                                f"замало українських фактів: {len(ua)} з {len(facts)}")


if __name__ == "__main__":
    unittest.main()
