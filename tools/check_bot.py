"""Перевірка бота і чату: чи живий токен і чи бот — адміністратор групи.

Запуск: python -m tools.check_bot
Потрібні змінні оточення TELEGRAM_BOT_TOKEN і TELEGRAM_CHAT_ID.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import telegram   # noqa: E402


def main() -> int:
    me = telegram.get_me()
    print(f"getMe:  ok  @{me['username']} (id {me['id']}, {me.get('first_name','')})")

    chat = telegram.get_chat()
    title = chat.get("title") or chat.get("username") or chat["id"]
    print(f"getChat: ok  «{title}» тип {chat['type']} (id {chat['id']})")

    member = telegram.get_chat_member(me["id"])
    status = member.get("status")
    print(f"Статус бота в чаті: {status}")
    if status not in ("administrator", "creator"):
        print("\n!! Бот НЕ адміністратор цього чату.")
        print("   Додайте його в групу і надайте право «Публікація повідомлень».")
        return 2
    if member.get("can_post_messages") is False:
        print("\n!! У бота немає права публікувати повідомлення.")
        return 2
    print("Усе гаразд: бот може публікувати.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
