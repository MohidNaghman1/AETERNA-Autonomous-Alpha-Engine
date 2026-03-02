# Example: send alert to all users with Telegram ID
from app.modules.identity.infrastructure.models import User
from sqlalchemy.orm import Session
import os
import asyncio
from telegram import Bot

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def send_telegram_alert(telegram_id: int, message: str):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.send_message(chat_id=telegram_id, text=message, parse_mode="Markdown")


# Example usage from backend:
def send_alert_to_telegram(telegram_id: int, message: str):
    asyncio.run(send_telegram_alert(telegram_id, message))


def send_alert_to_all_telegram_users(message: str, db_session: Session):
    users = db_session.query(User).filter(User.telegram_id.isnot(None)).all()
    for user in users:
        try:
            send_alert_to_telegram(int(user.telegram_id), message)
        except Exception as e:
            print(f"[TELEGRAM-ERROR] Failed to send to {user.email}: {e}")
