"""Фільтр контенту, пов'язаного з росією.

Блокуємо державу, її міста, установи, медіа, домени й символіку.
Фільтр застосовується ДВІЧІ:
  1) коли новина/знижка відбирається з зовнішнього джерела
     (`providers/deals.py`, `providers/evergreen.py`);
  2) безпосередньо перед відправкою в Telegram (`bot/telegram.py::_call`) —
     це остання лінія, повз неї не пройде жоден шлях публікації.

Окремо описаний виняток: художники українського походження, яких росія
собі привласнила. Їхні імена НІКОЛИ не потрапляють у BLOCK_PATTERNS —
див. RECLAIMED_ARTISTS і тести в tests/test_filters.py.
"""
import re
import unicodedata

# --- Художники, яких росія привласнила -----------------------------------
# Це не «дозволені слова», а документований перелік: жоден патерн нижче
# не має блокувати ці імена. Порушення ловить tests/test_filters.py.
RECLAIMED_ARTISTS = {
    "малевич": "Казимир Малевич — народився в Києві, 1879",
    "malevich": "Kazimir Malevich — born in Kyiv, 1879",
    "куїндж": "Архип Куїнджі — народився в Маріуполі, 1842",
    "kuindzhi": "Arkhip Kuindzhi — born in Mariupol, 1842",
    "рєпін": "Ілля Рєпін — народився в Чугуєві, 1844",
    "репін": "Ілля Рєпін — народився в Чугуєві, 1844",
    "repin": "Ilya Repin — born in Chuhuiv, 1844",
    "айвазовськ": "Іван Айвазовський — народився у Феодосії, 1817",
    "aivazovsky": "Ivan Aivazovsky — born in Feodosia, 1817",
    "делоне": "Соня (Софія) Делоне — народилася на Полтавщині, 1885",
    "delaunay": "Sonia Delaunay — born in Poltava region, 1885",
    "екстер": "Олександра Екстер — виросла в Києві",
    "архипенко": "Олександр Архипенко — народився в Києві, 1887",
    "боголюбов": "Олексій Боголюбов — мариніст, працював в Україні",
    "бурлюк": "Давид Бурлюк — народився на Харківщині, 1882",
    "ge ": "Микола Ге — жив і похований на Чернігівщині",
}

# --- Що блокуємо ----------------------------------------------------------
# Патерни шукаються у нормалізованому (нижній регістр, NFKC) тексті.
BLOCK_PATTERNS = [
    # держава / нація / мова
    r"\bросі", r"\bросія", r"\bросий", r"\bроссия", r"\bроссии", r"\bроссию",
    r"\bросійс", r"\bроссийс", r"\brussia", r"\brussian", r"\brussie",
    r"\brossi[jy]", r"\bросфедерац", r"\bрос\.\s?федерац",
    r"\bрф\b", r"\bросіянин", r"\bросіянк", r"\bрусск", r"\bрусич",
    r"\bмоскв", r"\bmoscow", r"\bмоскал", r"\bкремл", r"\bkremlin",
    r"\bпутін", r"\bпутин", r"\bputin", r"\bлавров", r"\bмедведєв", r"\bмедведев",
    # міста
    r"\bпетербур", r"\bpeterburg", r"\bpetersburg", r"\bленінград", r"\bленинград",
    r"\bказань\b", r"\bkazan\b", r"\bекатеринбур", r"\bєкатеринбур",
    r"\bновосибірс", r"\bновосибирс", r"\bсочі\b", r"\bсочи\b",
    r"\bвладивосток", r"\bнижн[ьі]й новгород", r"\bперм[ьі]\b", r"\bсамар[ае]\b",
    # установи / музеї / медіа / бренди
    r"\bермітаж", r"\bэрмитаж", r"\bhermitage", r"\bтретьяков", r"\bтретяков",
    r"\btretyakov", r"\bгараж\s+музе", r"\bпушкінськ(ий)?\s+музе",
    r"\bбольшой\s+театр", r"\bмаріїнськ(ий)?\s+театр", r"\bмариинск",
    r"\bросатом", r"\bгазпром", r"\bсбербанк", r"\bяндекс", r"\byandex",
    r"\bruptly", r"\brt\.com", r"\bспутник\s+ново", r"\btass\b", r"\bтасс\b",
    r"\bріа\s+новини", r"\bриа\s+новости", r"\binterfax\.ru", r"\bлентач",
    r"\blenta\.ru", r"\bмосфільм", r"\bмосфильм",
    # окупація / війна з боку рф
    r"\bокупант", r"\bz-?патріот", r"\bднр\b", r"\bлнр\b", r"\bwagner\b", r"\bвагнер",
    # домени й майданчики
    r"\.ru\b", r"\.su\b", r"\.рф\b", r"\brutube", r"\bvk\.com", r"\bvk\.ru",
    r"\bok\.ru", r"\bmail\.ru", r"\byandex\.",
]

# Фрази, які зовні схожі на заблоковані, але до росії стосунку не мають.
# Перед пошуком вони маскуються пробілами (довжина зберігається).
ALLOW_PATTERNS = [
    r"київська\s+русь", r"\bрусь\b", r"\bрусі\b", r"\bрусов\w*",
    r"\bрусин\w*", r"\bрусалк\w*", r"\bрусанівк\w*", r"\bрусяв\w*",
    r"\bбілорус\w*", r"\bпрусс?\w*", r"\bетруск\w*", r"\bетрусь\w*",
    r"\bказан\b", r"\bказані\b", r"\bказана\b",          # казан, а не місто
    r"\bсамарянин\w*", r"\bперміс\w*",
]

_COMPILED = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in BLOCK_PATTERNS]
_ALLOW = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in ALLOW_PATTERNS]


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    return text.lower().replace("\u0301", "")


def _mask_allowed(text: str) -> str:
    """Замінити дозволені фрази пробілами тієї ж довжини."""
    for rx in _ALLOW:
        text = rx.sub(lambda m: " " * len(m.group(0)), text)
    return text


def _prepare(parts) -> str:
    return _mask_allowed(_normalize(" ".join(p for p in parts if p)))


def is_blocked(*parts: str) -> bool:
    """True, якщо будь-яка з частин тексту містить росконтент."""
    text = _prepare(parts)
    if not text.strip():
        return False
    return any(rx.search(text) for rx in _COMPILED)


def reason(*parts: str) -> str | None:
    """Що саме спрацювало — для логів і діагностики."""
    text = _prepare(parts)
    for rx in _COMPILED:
        m = rx.search(text)
        if m:
            return m.group(0).strip()
    return None


def reclaimed(*parts: str) -> list[str]:
    """Які «привласнені» художники згадані — для діагностики банку."""
    text = _normalize(" ".join(p for p in parts if p))
    return [note for key, note in RECLAIMED_ARTISTS.items() if key in text]
