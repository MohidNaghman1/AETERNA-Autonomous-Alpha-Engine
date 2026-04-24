"""Telegram bot for account linking and alert delivery.

Provides Telegram commands for users to link their AETERNA accounts and receive alerts.
"""

import os
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.ext import MessageHandler, filters
import re
from dotenv import load_dotenv
from app.config.db import AsyncSessionLocal
from app.modules.identity.infrastructure.models import User

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - prompt user to link their email.

    Args:
        update: Telegram update object
        context: Command context
    """
    await update.message.reply_text(
        "👋 Welcome to AETERNA!\n\nReply with your registered email to link your account.\nType /help for instructions."
    )


async def link_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle email response to link user account.

    Validates email format and links the user's Telegram chat ID to their account.

    Args:
        update: Telegram update object
        context: Command context
    """
    email = update.message.text.strip()
    chat_id = update.message.chat_id
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        async with AsyncSessionLocal() as session:
            result = await session.execute(session.query(User).filter_by(email=email))
            user = result.scalars().first()
            if user:
                user.telegram_id = str(chat_id)
                await session.commit()
                await update.message.reply_text(
                    f"✅ Your account is linked! You will now receive alerts for {email}."
                )
            else:
                await update.message.reply_text(
                    "❌ Email not found in user database. Please register first or check your email."
                )
    else:
        await update.message.reply_text(
            "❌ Invalid email address. Please send a valid email."
        )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - report bot status.

    Args:
        update: Telegram update object
        context: Command context
    """
    await update.message.reply_text(
        "✅ AETERNA bot is running. Alerts will be sent as they occur."
    )


async def alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /alerts command - show user's recent alerts.

    Args:
        update: Telegram update object
        context: Command context
    """
    await update.message.reply_text("ℹ️ No alerts yet. (Demo)")


async def demoalert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /demoalert command - send a demo alert to the user.

    Args:
        update: Telegram update object
        context: Command context
    """
    chat_id = update.message.chat_id
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            session.query(User).filter_by(telegram_id=str(chat_id))
        )
        user = result.scalars().first()
        email = user.email if user else None
    if email:
        await send_alert_to_user(
            email, f"🚨 Demo alert for {email}! This is how alerts will look."
        )
        await update.message.reply_text(f"✅ Demo alert sent to {email}!")
    else:
        await update.message.reply_text(
            "❌ No email linked to this chat. Please send your email first."
        )


async def send_alert_to_user(email: str, message: str) -> None:
    """Send a Telegram message to a user by their email.

    Args:
        email: User's email address
        message: Message text to send
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(session.query(User).filter_by(email=email))
        user = result.scalars().first()
        telegram_id = user.telegram_id if user else None
    if telegram_id:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=telegram_id, text=message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show available commands.

    Args:
        update: Telegram update object
        context: Command context
    """
    help_text = (
        "AETERNA Telegram Bot Help\n\n"
        "/start - Begin linking your account\n"
        "/help - Show this help message\n"
        "/status - Check bot status\n"
        "/alerts - Show your alerts\n"
        "/demoalert - Send a demo alert\n\n"
        "To link your account, reply with your registered email.\n"
        "If you need support, contact admin."
    )
    await update.message.reply_text(help_text)


def main() -> None:
    """Start the Telegram bot and initialize all command handlers."""
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set. Check your .env file.")
        return
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("alerts", alerts))
    app.add_handler(CommandHandler("demoalert", demoalert))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_email))
    print("Telegram bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
