"""Мінімальний клієнт Telegram Bot API.

Тут же — остання (друга) перевірка фільтром: жоден шлях публікації не може
обійти `_call`, тому росконтент фізично не має як потрапити в групу.
"""
import os
from urllib.parse import urlsplit

import requests

from .config import TELEGRAM_API
from .filters import is_blocked, reason

CAPTION_LIMIT = 1024
MESSAGE_LIMIT = 4096


class TelegramError(RuntimeError):
    pass


class BlockedContentError(RuntimeError):
    """Спрацював фільтр росконтенту прямо перед відправкою."""


def _creds():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise TelegramError("Не задано TELEGRAM_BOT_TOKEN або TELEGRAM_CHAT_ID")
    return token, chat_id


def _guard(payload: dict) -> None:
    """Друге застосування фільтра — безпосередньо перед sendMessage/sendPhoto.

    У фото перевіряємо лише домен: ім'я файлу на upload.wikimedia.org — це
    службові метадані, які глядач не бачить (у сканів музейних збірок туди
    часто зашито назву колекції). Домен же перевіряти обов'язково.
    """
    parts = [str(payload.get("text", "")), str(payload.get("caption", ""))]
    photo = str(payload.get("photo", ""))
    if photo:
        parts.append(urlsplit(photo).netloc)
    if is_blocked(*parts):
        raise BlockedContentError(
            f"Фільтр зупинив публікацію просто перед відправкою: {reason(*parts)}")


def _call(method: str, payload: dict) -> dict:
    token, chat_id = _creds()
    _guard(payload)
    payload = {"chat_id": chat_id, **payload}
    thread = os.environ.get("TELEGRAM_THREAD_ID", "").strip()
    if thread:
        payload["message_thread_id"] = int(thread)
    r = requests.post(f"{TELEGRAM_API}/bot{token}/{method}", json=payload, timeout=45)
    try:
        data = r.json()
    except ValueError:
        data = {}
    if not data.get("ok"):
        raise TelegramError(
            f"{method} -> {r.status_code} {data.get('description') or r.text[:300]}")
    return data["result"]


def send_message(text: str, preview: bool = True) -> dict:
    return _call("sendMessage", {
        "text": text[:MESSAGE_LIMIT],
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": not preview},
    })


def send_photo(photo_url: str, caption: str) -> dict:
    if len(caption) > CAPTION_LIMIT:
        raise TelegramError(
            f"Підпис до фото {len(caption)} символів — ліміт Telegram {CAPTION_LIMIT}")
    return _call("sendPhoto", {
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    })


def get_me() -> dict:
    return _get("getMe")


def get_chat() -> dict:
    _, chat_id = _creds()
    return _get("getChat", {"chat_id": chat_id})


def get_chat_member(user_id: int) -> dict:
    _, chat_id = _creds()
    return _get("getChatMember", {"chat_id": chat_id, "user_id": user_id})


def _get(method: str, params: dict | None = None) -> dict:
    token, _ = _creds()
    r = requests.get(f"{TELEGRAM_API}/bot{token}/{method}", params=params or {}, timeout=30)
    try:
        data = r.json()
    except ValueError:
        data = {}
    if not data.get("ok"):
        raise TelegramError(f"{method}: {data.get('description') or r.text[:200]}")
    return data["result"]
