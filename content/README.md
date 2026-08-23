# Як додати свій контент

Редагуйте `tools/build_bank_1.py` (факти) або `tools/build_bank_2.py` (меми, картина дня),
потім запустіть:

```bash
python tools/build_bank.py
```

Скрипт перезбирає `evergreen.json` і **відмовиться** зібрати банк,
якщо у тексті знайдеться росконтент.

Формат елемента в `evergreen.json`:

```json
{"id": "fact-043", "type": "fact", "text": "текст із HTML-розміткою Telegram"}
{"id": "art-036",  "type": "artwork", "wiki": "Mona_Lisa", "lang": "en", "text": "підпис до фото (до 1024 символів)"}
```

`type`: `fact` | `meme` | `artwork`.
Для `artwork` зображення підтягується з Вікіпедії за назвою статті у полі `wiki`.
