"""
Delivery module for sending alerts via different channels (email, telegram, etc).
"""
import asyncio
from app.config.db import AsyncSessionLocal
from app.modules.identity.infrastructure.models import User
from telegram import Bot
import os
from app.shared.utils.email_utils import send_email_alert

def deliver_email_alert(alert, user_prefs):
    email = user_prefs.get("email")
    email_frequency = user_prefs.get("email_frequency", "immediate")
    unsubscribe = user_prefs.get("unsubscribe", False)
    if not email or unsubscribe or email_frequency == "off":
        return False
    if email_frequency == "immediate":
        send_email_alert(
            to_email=email,
            subject=alert["title"],
            html_content=alert["body"]
        )
        return True
    elif email_frequency == "daily_digest":
        try:
            from app.modules.delivery.application.digest_tasks import add_alert_to_digest
            add_alert_to_digest(email, alert)
            return True
        except Exception as e:
            print(f"[EMAIL-ERROR][Digest] Failed to add alert to digest: {e}")
            return False
    return False


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def send_alert_via_bot(telegram_id, message):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.send_message(chat_id=telegram_id, text=message, parse_mode="Markdown")

def deliver_telegram_alert(alert, user_prefs):
    email = user_prefs.get("email")
    if not email:
        return False
    async def send():
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                session.query(User).filter_by(email=email)
            )
            user = result.scalars().first()
            telegram_id = user.telegram_id if user else None
            if telegram_id:
                await send_alert_via_bot(telegram_id, f"{alert['title']}\n{alert['body']}")
                return True
            else:
                print(f"[TELEGRAM-ERROR] No telegram_id for email: {email}")
                return False
    return asyncio.run(send())

# Future: add deliver_websocket_alert, etc.
