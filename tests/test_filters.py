# -*- coding: utf-8 -*-
"""Тести фільтра росконтенту та винятку для привласнених художників."""
import json
import unittest
from pathlib import Path

from bot.filters import RECLAIMED_ARTISTS, is_blocked, reason, reclaimed

BANK = json.loads((Path(__file__).resolve().parent.parent / "content" / "evergreen.json")
                  .read_text(encoding="utf-8"))


class TestBlocked(unittest.TestCase):
    MUST_BLOCK = [
        "Ермітаж",
        "Москва",
        "Russian museum",
        "example.ru",
        "Виставка в Ермітажі відкрилась",
        "Третьяковська галерея",
        "Санкт-Петербург",
        "The State Hermitage Museum announced",
        "https://vk.com/some_art_page",
        "rutube.ru/video/123",
        "новини на lenta.ru",
        "росія вкрала колекцію",
        "російський художник",
        "Russia banned the exhibition",
        "домен example.su",
        "яндекс.колекція",
        "ТАСС повідомляє",
        "окупанти вивезли скіфське золото",
    ]

    MUST_PASS = [
        "Малевич народився у Києві",
        "Київська Русь",
        "Рєпін народився у Чугуєві",
        "Виставка в Луврі",
        "Айвазовський народився у Феодосії",
        "Куїнджі народився в Маріуполі",
        "Соня Делоне народилася на Полтавщині",
        "Казимир Малевич, «Чорний квадрат», 1915",
        "фарбу варили в казані на вогні",
        "білоруський художник у Варшаві",
        "етруски розписували гробниці",
        "прусська блакить — той самий берлінський блакитний",
        "Марія Примаченко, «Звір гуляє»",
        "Виставка Архипенка в Києві",
        "https://artslooker.com/vystavka",
        "",
    ]

    def test_blocked(self):
        for text in self.MUST_BLOCK:
            with self.subTest(text=text):
                self.assertTrue(is_blocked(text), f"НЕ заблоковано: {text!r}")
                self.assertIsNotNone(reason(text))

    def test_not_blocked(self):
        for text in self.MUST_PASS:
            with self.subTest(text=text):
                self.assertFalse(is_blocked(text),
                                 f"Хибне спрацювання на {text!r}: {reason(text)}")

    def test_multipart(self):
        self.assertTrue(is_blocked("Гарна виставка", "джерело: news.ru"))
        self.assertFalse(is_blocked("Гарна виставка", "джерело: artslooker.com"))


class TestReclaimedArtists(unittest.TestCase):
    """Виняток, який не можна зламати: привласнені росією українці."""

    CASES = [
        "Малевич", "Казимир Малевич", "Kazimir Malevich",
        "Куїнджі", "Архип Куїнджі", "Kuindzhi",
        "Рєпін", "Ілля Рєпін", "Repin",
        "Айвазовський", "Іван Айвазовський", "Aivazovsky",
        "Делоне", "Соня Делоне", "Sonia Delaunay",
        "Олександра Екстер", "Олександр Архипенко", "Давид Бурлюк",
    ]

    def test_names_never_blocked(self):
        for name in self.CASES:
            with self.subTest(name=name):
                self.assertFalse(is_blocked(name),
                                 f"Привласненого художника заблоковано: {name} ({reason(name)})")

    def test_with_ukrainian_context(self):
        for text in [
            "Казимир Малевич народився в Києві 1879 року",
            "Архип Куїнджі — уродженець Маріуполя",
            "Ілля Рєпін народився в Чугуєві на Харківщині",
            "Іван Айвазовський провів у Феодосію водогін власним коштом",
            "Соня Делоне народилася в Градизьку на Полтавщині",
        ]:
            with self.subTest(text=text):
                self.assertFalse(is_blocked(text), f"{text} -> {reason(text)}")
                self.assertTrue(reclaimed(text), "reclaimed() має розпізнати художника")

    def test_reclaimed_names_absent_from_block_patterns(self):
        """Жодне ім'я з переліку не має самé по собі вмикати фільтр."""
        for key in RECLAIMED_ARTISTS:
            with self.subTest(key=key):
                self.assertFalse(is_blocked(f"художник {key.strip()} і його роботи"))

    def test_present_in_bank(self):
        """Ці художники мають бути в банку з українським контекстом."""
        blob = json.dumps(BANK, ensure_ascii=False).lower()
        for key in ("малевич", "куїндж", "рєпін", "айвазовськ", "делоне"):
            with self.subTest(key=key):
                self.assertIn(key, blob, f"У банку немає жодного посту про {key}")

    def test_ros_framing_still_blocked(self):
        """Ім'я не є індульгенцією: російське обрамлення все одно блокується."""
        self.assertTrue(is_blocked("Малевич — великий російський художник"))
        self.assertTrue(is_blocked("Рєпін у Третьяковській галереї"))


if __name__ == "__main__":
    unittest.main()
