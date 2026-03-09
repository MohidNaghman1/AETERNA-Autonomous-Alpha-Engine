"""Multi-channel alert delivery system.

Handles alert delivery via multiple channels:
- Email (immediate or daily digest)
- Telegram (via Telegram Bot API)
- WebSocket (future implementation)

All async operations use AsyncSessionLocal with proper context managers.
"""

from app.config.db import AsyncSessionLocal
from app.modules.identity.infrastructure.models import User
from telegram import Bot
from telegram.error import TelegramError
from sqlalchemy import select
import os
import logging
from app.shared.utils.email_utils import send_email_alert
from app.modules.delivery.application.telegram_alert_utils import (
    build_telegram_alert_message,
)

logger = logging.getLogger(__name__)


def deliver_email_alert(alert: dict, user_prefs: dict) -> bool:
    """
    Deliver alert via email according to user preferences.

    Args:
        alert: Alert object with 'title', 'body', and enriched fields (quality_score, risk_score, etc.)
        user_prefs: User preferences dict with 'email', 'email_frequency', 'unsubscribe'

    Returns:
        bool: True if delivery initiated successfully, False otherwise

    Raises:
        No exceptions - all errors are logged and False is returned
    """
    email = user_prefs.get("email")
    email_frequency = user_prefs.get("email_frequency", "immediate")
    unsubscribe = user_prefs.get("unsubscribe", False)
    if not email or unsubscribe or email_frequency == "off":
        return False

    # Build enriched HTML email content
    html_content = _build_alert_email_html(alert)

    if email_frequency == "immediate":
        try:
            send_email_alert(
                to_email=email,
                subject=alert["title"],
                html_content=html_content,
            )
            logger.info(f"[EMAIL] Alert sent to {email}")
            return True
        except Exception as e:
            logger.error(f"[EMAIL-ERROR] Failed to send to {email}: {e}")
            return False

    elif email_frequency == "daily_digest":
        try:
            from app.modules.delivery.application.digest_tasks import (
                add_alert_to_digest,
            )

            add_alert_to_digest(email, alert)
            logger.info(f"[EMAIL-DIGEST] Alert added to digest for {email}")
            return True
        except Exception as e:
            logger.error(
                f"[EMAIL-ERROR][Digest] Failed to add alert to digest for {email}: {e}"
            )
            return False
    return False


def _build_alert_email_html(alert: dict) -> str:
    """Build enriched HTML email content from alert with enhanced fields."""
    html_parts = [f"<p><strong>{alert.get('body', '')}</strong></p>"]

    # Priority badge
    priority = alert.get("priority", "LOW")
    priority_color = {"HIGH": "#ff4444", "MEDIUM": "#ffaa00", "LOW": "#00aa00"}.get(
        priority, "#999"
    )
    html_parts.append(
        f'<p><span style="background-color: {priority_color}; color: white; padding: 5px 10px; border-radius: 5px;"><strong>Priority: {priority}</strong></span></p>'
    )

    # Quality/Risk scores
    if alert.get("quality_score") is not None:
        html_parts.append(
            f'<p>📊 <strong>Content Quality Score:</strong> {alert.get("quality_score")}/100</p>'
        )

    if alert.get("risk_score") is not None:
        html_parts.append(
            f'<p>⚠️  <strong>Crypto Risk Score:</strong> {alert.get("risk_score")}/100</p>'
        )

    if alert.get("volatility"):
        html_parts.append(
            f'<p>📈 <strong>Volatility:</strong> {alert.get("volatility").upper()}</p>'
        )

    if alert.get("read_time_minutes"):
        html_parts.append(
            f'<p>⏱️  <strong>Read Time:</strong> ~{alert.get("read_time_minutes")} minutes</p>'
        )

    # Alert reasons (for price alerts)
    if alert.get("alert_reasons"):
        html_parts.append(
            f'<p>🔔 <strong>Alert Reason:</strong> {alert.get("alert_reasons")}</p>'
        )

    # URLs (for news)
    urls = alert.get("urls", [])
    if urls:
        html_parts.append("<p><strong>📚 Related Links:</strong><br>")
        for url in urls[:3]:
            html_parts.append(f'  <a href="{url}">→ {url[:60]}...</a><br>')
        html_parts.append("</p>")

    # Hashtags (for news)
    hashtags = alert.get("hashtags", [])
    if hashtags:
        hashtags_str = " ".join([f"<code>#{tag}</code>" for tag in hashtags[:5]])
        html_parts.append(f"<p><strong>🏷️  Topics:</strong> {hashtags_str}</p>")

    return "\n".join(html_parts)


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def send_alert_via_bot(telegram_id: int, message: str) -> bool:
    """Send alert message via Telegram Bot API.

    Args:
        telegram_id: User's Telegram chat ID (must be integer)
        message: Message text to send (supports Markdown formatting)

    Returns:
        bool: True if message sent successfully, False on error
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error("[TELEGRAM] TELEGRAM_BOT_TOKEN not configured in environment")
        return False

    if not telegram_id or not message:
        logger.warning(f"[TELEGRAM] Invalid parameters: telegram_id={telegram_id}")
        return False

    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=telegram_id, text=message, parse_mode="Markdown")
        logger.info(f"[TELEGRAM] Message sent to user {telegram_id}")
        return True

    except TelegramError as e:
        logger.error(f"[TELEGRAM-ERROR] Telegram API error for user {telegram_id}: {e}")
        return False

    except Exception as e:
        logger.error(
            f"[TELEGRAM-ERROR] Unexpected error sending to {telegram_id}: {type(e).__name__}: {e}"
        )
        return False


async def deliver_telegram_alert(alert: dict, user_prefs: dict) -> bool:
    """Deliver alert via Telegram according to user preferences.

    Retrieves user's Telegram account link and sends enriched alert message with
    quality_score, risk_score, and other metadata.

    Args:
        alert: Alert object with 'title', 'body', and enriched fields
        user_prefs: User preferences dict with 'email' key

    Returns:
        bool: True if Telegram delivery successful, False on any error
    """
    email = user_prefs.get("email")
    if not email:
        logger.warning("[TELEGRAM] No email in user preferences")
        return False

    try:
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            user = result.scalars().first()

            if not user:
                logger.warning(f"[TELEGRAM] User not found for email: {email}")
                return False

            telegram_id = user.telegram_id
            if not telegram_id:
                logger.info(f"[TELEGRAM] User {email} has no Telegram account linked")
                return False

            # Build enriched message with new fields
            message = build_telegram_alert_message(alert)

            success = await send_alert_via_bot(telegram_id, message)
            return success

    except Exception as e:
        logger.error(
            f"[TELEGRAM-ERROR] Unexpected error in deliver_telegram_alert: {type(e).__name__}: {e}"
        )
        return False
