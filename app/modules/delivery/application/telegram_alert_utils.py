# Example: send alert to all users with Telegram ID
from app.modules.identity.infrastructure.models import User
from sqlalchemy.orm import Session
import os
import asyncio
from telegram import Bot
from typing import Dict, Any

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


def build_telegram_alert_message(alert: Dict[str, Any]) -> str:
    """Build enriched Telegram message from alert dict with enhanced fields.
    
    Args:
        alert: Alert dict with title, body, and enriched fields
        
    Returns:
        str: Formatted Telegram message with Markdown support
    """
    lines = []
    
    # Priority emoji and title
    priority = alert.get("priority", "LOW")
    emoji = {"HIGH": "🚨", "MEDIUM": "⚠️ ", "LOW": "ℹ️ "}.get(priority, "📌")
    lines.append(f"{emoji} *{alert.get('title', 'Alert')}*")
    
    # Main body
    body = alert.get("body", "").strip()
    if body:
        lines.append(f"\n{body}")
    
    # Risk score (prices)
    risk_score = alert.get("risk_score")
    if risk_score is not None:
        risk_level = "🔴 HIGH" if risk_score >= 70 else ("🟡 MEDIUM" if risk_score >= 40 else "🟢 LOW")
        lines.append(f"\n*Risk:* {risk_level} ({risk_score}/100)")
    
    # Quality score (news)
    quality_score = alert.get("quality_score")
    if quality_score is not None:
        lines.append(f"*Quality:* {quality_score}/100")
    
    # Volatility (prices)
    volatility = alert.get("volatility")
    if volatility:
        volatility_emoji = {"high": "📈", "medium": "➡️ ", "low": "📉"}.get(volatility.lower(), "〰️ ")
        lines.append(f"*Volatility:* {volatility_emoji} {volatility.upper()}")
    
    # Alert reason (prices)
    alert_reasons = alert.get("alert_reasons")
    if alert_reasons:
        lines.append(f"*Reason:* {alert_reasons}")
    
    # Read time (news)
    read_time = alert.get("read_time_minutes")
    if read_time:
        lines.append(f"*Read Time:* ~{read_time} min")
    
    # Hashtags (news)
    hashtags = alert.get("hashtags", [])
    if hashtags:
        hashtags_str = " ".join([f"`#{tag}`" for tag in hashtags[:5]])
        lines.append(f"*Topics:* {hashtags_str}")
    
    # URLs (news)
    urls = alert.get("urls", [])
    if urls:
        url_text = ", ".join([f"[Link]({url})" for url in urls[:2]])
        lines.append(f"*Sources:* {url_text}")
    
    # Priority info
    lines.append(f"\n_Priority: {priority}_")
    
    return "\n".join(lines)
