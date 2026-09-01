"""Налаштування автопостера."""
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Kyiv")

# Слоти публікацій за київським часом (година дня).
# Скрипт запускається щочверть години і сам вирішує, чи час постити.
SLOTS = [10, 15, 20]

# Скільки живе слот, якщо після нього немає іншого (тобто вечірній 20:00):
# рівно стільки хвилин, щоб пост не прилетів о 3-й ночі після збою раннера.
SLOT_GRACE_MINUTES = 150

# Слот, після якого ще будуть інші, живе до початку наступного мінус цей
# буфер. Тобто 10:00 -> до 14:30, 15:00 -> до 19:30, 20:00 -> до 22:30.
# Так пост не губиться, навіть якщо GitHub не запускав крон пів дня,
# і водночас два пости не виходять один за одним.
SLOT_GAP_MINUTES = 30

# План контенту: слот -> (бажаний тип, запасні типи)
# Типи: deals | fact | artwork | meme
SLOT_PLAN = {
    10: ["fact", "artwork", "meme"],
    15: ["artwork", "fact", "meme"],
    20: ["meme", "fact", "artwork"],
}

# У ці дні тижня (0=пн) о 15:00 замість «картини дня» шукаємо знижки
DEALS_WEEKDAYS = {1, 4}  # вівторок і п'ятниця

# --- Джерела знижок на художні матеріали ---------------------------------
DEALS_SOURCES = [
    {"name": "ARTIZO", "url": "https://artizo.com.ua/spetsialni-propozytsii/rozprodazh/",
     "home": "https://artizo.com.ua/"},
    {"name": "Азур", "url": "https://azur.com.ua/", "home": "https://azur.com.ua/"},
    {"name": "Майстерня (masterica)", "url": "https://masterica.com.ua/ua/aktsionnye-tovary/",
     "home": "https://masterica.com.ua/ua/"},
    {"name": "Monet.ua", "url": "https://monet.ua/discounted", "home": "https://monet.ua/"},
    {"name": "ArtSklad", "url": "https://artsklad.ua/catalog/aktsijni-propozitsii",
     "home": "https://artsklad.ua/"},
]

TELEGRAM_API = "https://api.telegram.org"
