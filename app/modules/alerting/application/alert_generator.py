"""
Alert Generator: Creates alerts for HIGH and MEDIUM priority events.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, time
import collections
from app.shared.utils.email_utils import send_email_alert
from app.modules.delivery.application.delivery import deliver_email_alert

# Example alert structure

# --- In-memory rate limit tracker (for demo; use Redis in prod) ---
user_alert_times = collections.defaultdict(list)  # user_id -> [datetime]

def filter_channels_by_prefs(user_prefs: Dict[str, Any], channels: List[str]) -> List[str]:
    allowed = user_prefs.get("channels", channels)
    return [ch for ch in channels if ch in allowed]

def is_within_quiet_hours(user_prefs: Dict[str, Any]) -> bool:
    quiet = user_prefs.get("quiet_hours")
    if not quiet:
        return False
    now = datetime.utcnow().time()
    start = time.fromisoformat(quiet["start"])
    end = time.fromisoformat(quiet["end"])
    if start < end:
        return start <= now < end
    else:
        return now >= start or now < end

def is_rate_limited(user_id: str, max_alerts: int = 10) -> bool:
    now = datetime.utcnow()
    times = user_alert_times[user_id]
    # Remove alerts older than 1 hour
    user_alert_times[user_id] = [t for t in times if (now - t).total_seconds() < 3600]
    return len(user_alert_times[user_id]) >= max_alerts

def record_alert_time(user_id: str):
    user_alert_times[user_id].append(datetime.utcnow())

def generate_alert(event: Dict[str, Any], user_prefs: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if event.get("priority") not in ("HIGH", "MEDIUM"):
        return None
    user_id = event.get("user_id")
    user_prefs = user_prefs or {}
    # Rate limiting
    if user_id and is_rate_limited(user_id):
        return None
    # Quiet hours
    if is_within_quiet_hours(user_prefs):
        return None
    # Filter channels
    channels = filter_channels_by_prefs(user_prefs, ["telegram", "email", "web"])
    if not channels:
        return None
    alert = {
        "alert_id": f"alert_{event.get('id')}",
        "user_id": user_id,
        "event_id": event.get("id"),
        "priority": event.get("priority"),
        "score": event.get("score"),
        "timestamp": datetime.utcnow().isoformat(),
        "channels": channels,
        "title": event.get("title", "New Event Alert"),
        "body": event.get("summary", event.get("text", "")),
        "raw_event": event,
        "status": "unread"
    }
    if user_id:
        record_alert_time(user_id)
    # Email delivery via delivery module
    if "email" in alert["channels"]:
        deliver_email_alert(alert, user_prefs)
    return alert
