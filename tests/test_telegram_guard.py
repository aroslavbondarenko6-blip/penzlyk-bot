# -*- coding: utf-8 -*-
"""Друге застосування фільтра — безпосередньо перед відправкою."""
import unittest

from bot import telegram


class TestGuard(unittest.TestCase):
    def test_guard_blocks_text(self):
        with self.assertRaises(telegram.BlockedContentError):
            telegram._guard({"text": "Виставка в Ермітажі"})

    def test_guard_blocks_photo_url(self):
        with self.assertRaises(telegram.BlockedContentError):
            telegram._guard({"caption": "Гарна картина", "photo": "https://cdn.example.ru/a.jpg"})

    def test_guard_allows_wikimedia_filename_with_collection_name(self):
        """Назва колекції всередині імені файлу не має зривати пост про Малевича."""
        telegram._guard({
            "caption": "🖼 «Чорний квадрат» — Казимир Малевич, 1915. Народився в Києві.",
            "photo": "https://upload.wikimedia.org/wikipedia/commons/d/dc/"
                     "Kazimir_Malevich%2C_1915%2C_Black_Suprematic_Square%2C_"
                     "Tretyakov_Gallery%2C_Moscow.jpg",
        })

    def test_guard_still_blocks_ros_domain_even_for_photo(self):
        with self.assertRaises(telegram.BlockedContentError):
            telegram._guard({"caption": "Картина", "photo": "https://img.gallery.ru/x.jpg"})

    def test_guard_allows_clean(self):
        telegram._guard({"text": "Малевич народився в Києві",
                         "photo": "https://upload.wikimedia.org/a.jpg"})

    def test_send_photo_rejects_long_caption(self):
        with self.assertRaises(telegram.TelegramError):
            telegram.send_photo("https://example.com/a.jpg", "я" * (telegram.CAPTION_LIMIT + 1))

    def test_missing_credentials_raise(self):
        import os
        saved = os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        try:
            with self.assertRaises(telegram.TelegramError):
                telegram._creds()
        finally:
            if saved:
                os.environ["TELEGRAM_BOT_TOKEN"] = saved


if __name__ == "__main__":
    unittest.main()
