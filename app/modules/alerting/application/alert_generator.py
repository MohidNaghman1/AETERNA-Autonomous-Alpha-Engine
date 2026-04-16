"""Alert generation and filtering logic.

Creates alerts for HIGH and MEDIUM priority events and applies user preference filters
including quiet hours, rate limiting, and channel preferences.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, time
import collections
from app.shared.utils.email_utils import send_email_alert
from app.modules.delivery.application.delivery import deliver_email_alert
from app.modules.alerting.infrastructure.models import Alert
from app.config.db import SessionLocal

user_alert_times = collections.defaultdict(list)


def filter_channels_by_prefs(
    user_prefs: Dict[str, Any], channels: List[str]
) -> List[str]:
    """Filter alert delivery channels based on user preferences.

    Args:
        user_prefs: User preferences dict with 'channels' key
        channels: List of available channels to filter

    Returns:
        List of channels allowed by user preferences
    """
    if not user_prefs:
        return channels
    allowed = user_prefs.get("channels", channels)
    return [ch for ch in channels if ch in allowed]


def is_within_quiet_hours(user_prefs: Dict[str, Any]) -> bool:
    """Check if current time is within user's quiet hours.

    Args:
        user_prefs: User preferences dict with 'quiet_hours' key ({"start": "HH:MM", "end": "HH:MM"})

    Returns:
        bool: True if current time is within quiet hours, False otherwise
    """
    if not user_prefs:
        return False
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
    """Check if user has exceeded alert rate limit.

    Tracks alerts per user in a sliding 1-hour window.

    Args:
        user_id: User ID to check
        max_alerts: Maximum alerts allowed per hour

    Returns:
        bool: True if user has exceeded rate limit, False otherwise
    """
    now = datetime.utcnow()
    times = user_alert_times[user_id]
    user_alert_times[user_id] = [t for t in times if (now - t).total_seconds() < 3600]
    return len(user_alert_times[user_id]) >= max_alerts


def record_alert_time(user_id: str) -> None:
    """Record when an alert was sent to a user.

    Args:
        user_id: User ID who received the alert
    """
    user_alert_times[user_id].append(datetime.utcnow())


def save_alert(alert: dict) -> Alert:
    """Save alert to database.

    Args:
        alert: Alert dict with user_id, event_id, channels, status

    Returns:
        Alert: Saved alert model or None if save failed
    """
    db = SessionLocal()
    try:
        # System/broadcast alerts use user_id = None
        user_id = alert.get("user_id")
        if user_id is not None:
            user_id = int(user_id)
        # else: keep as None for system broadcasts

        # Event ID can be None for some alerts
        event_id = alert.get("event_id")
        if event_id is not None:
            event_id = int(event_id)

        # Idempotency guard: retries or duplicate processing should not create
        # multiple alert rows for the same event/user pair.
        existing_alert_query = db.query(Alert).filter(Alert.event_id == event_id)
        if user_id is None:
            existing_alert_query = existing_alert_query.filter(Alert.user_id.is_(None))
        else:
            existing_alert_query = existing_alert_query.filter(Alert.user_id == user_id)

        existing_alert = existing_alert_query.first()
        if existing_alert:
            print(
                f"[DB] Skipped duplicate alert for event {event_id} and user {user_id}"
            )
            return existing_alert

        db_alert = Alert(
            user_id=user_id,  # None for system/broadcast alerts
            event_id=event_id,
            channels=alert.get("channels", []),
            priority=alert.get("priority", "MEDIUM"),
            status=alert.get("status", "pending"),
            created_at=datetime.utcnow(),
        )
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)
        print(f"[DB] Saved alert {alert.get('alert_id', 'unknown')} for user {user_id}")
        return db_alert
    except Exception as e:
        db.rollback()
        print(f"[DB] Failed to save alert: {str(e)}")
        return None
    finally:
        db.close()


def generate_alert(
    event: Dict[str, Any], user_prefs: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Generate an alert from an event if it meets filters.

    Applies priority, rate limiting, quiet hours, and channel preference filters.
    Saves alert to database and triggers email delivery if configured.

    Args:
        event: Event dict with id, priority, score, title, summary/text, user_id
        user_prefs: User preferences dict for filtering, or None

    Returns:
        dict: Generated alert or None if filtered out
    """
    event_id = event.get("id", "unknown")
    priority = event.get("priority")

    if priority not in ("HIGH", "MEDIUM"):
        print(
            f"[ALERT-FILTER] Event {event_id}: Priority {priority} not HIGH/MEDIUM - SKIPPED"
        )
        return None

    user_id = event.get("user_id")
    user_prefs = user_prefs or {}

    if user_id and is_rate_limited(user_id):
        print(f"[ALERT-FILTER] Event {event_id} User {user_id}: Rate limited - SKIPPED")
        return None

    if is_within_quiet_hours(user_prefs):
        print(f"[ALERT-FILTER] Event {event_id}: Quiet hours - SKIPPED")
        return None

    channels = filter_channels_by_prefs(user_prefs, ["telegram", "email", "web"])
    if not channels:
        print(f"[ALERT-FILTER] Event {event_id}: No channels available - SKIPPED")
        return None

    #  NEW: Check Agent B profiling for priority boost
    agent_b = event.get("agent_b", {})
    alert_priority = priority  # Default to original priority

    if agent_b.get("should_boost_priority"):
        alert_priority = "CRITICAL"
        print(
            f"[ALERT-BOOST] Event {event_id}: Priority boosted {priority}→CRITICAL "
            f"({agent_b.get('priority_boost_reason')})"
        )

    print(
        f"[ALERT-GENERATE] Event {event_id}: Passed all filters. Priority={alert_priority}, Channels={channels}"
    )
    # Extract content dict (where enriched fields are stored)
    content = event.get("content", {}) if isinstance(event.get("content"), dict) else {}

    # Extract content dict (where enriched fields are stored)
    content = event.get("content", {}) if isinstance(event.get("content"), dict) else {}

    alert = {
        "alert_id": f"alert_{event.get('id')}",
        "user_id": user_id,
        "event_id": event.get("id"),
        "priority": alert_priority,  # ✅ Use boosted priority
        "score": event.get("score"),
        "timestamp": datetime.utcnow().isoformat(),
        "channels": channels,
        "title": event.get("title", content.get("title", "New Event Alert")),
        "body": event.get("summary", event.get("text", content.get("summary", ""))),
        "raw_event": event,
        "status": "pending",
        # Core content metadata
        "author": content.get("author"),  # Original author (news)
        "source": content.get("source"),  # Source (coindesk, cointelegraph, etc)
        "categories": content.get("categories", [])[:5],  # Top 5 categories
        # Crypto-specific enrichment (RSS extracted)
        "mentions": content.get("mentions", [])[
            :10
        ],  # Top 10 crypto entities mentioned
        "hashtags": content.get("hashtags", [])[:5],  # Top 5 hashtags
        # Content quality metrics
        "quality_score": content.get("quality_score"),  # News content quality (0-100)
        "word_count": content.get("word_count"),  # Total words in content
        "read_time_minutes": content.get(
            "read_time_minutes"
        ),  # Estimated read time (news)
        # Price-specific metrics (for price events)
        "risk_score": content.get("risk_score"),  # Crypto risk score (0-100)
        "volatility": content.get("price_volatility_category"),  # high/medium/low
        "alert_reasons": content.get("alert_reasons"),  # Why alert was triggered
        # References
        "urls": content.get("urls", [])[:3],  # Top 3 relevant URLs
        "link": content.get("link"),  # Original source link
        #  NEW: Agent B profiling data
        "agent_b_profiling": (
            {
                "entity_identified": agent_b.get("entity_identified"),
                "entity_id": agent_b.get("entity_id"),
                "entity_name": agent_b.get("entity_name"),
                "entity_type": agent_b.get("entity_type"),
                "wallet_address": agent_b.get("wallet_address"),
                "wallet_win_rate": agent_b.get("wallet_win_rate"),
                "wallet_tier": agent_b.get("wallet_tier"),
                "confidence_score": agent_b.get("confidence_score"),
                "profiling_signal": agent_b.get("profiling_signal"),
                "should_boost_priority": agent_b.get("should_boost_priority"),
                "priority_boost_reason": agent_b.get("priority_boost_reason"),
            }
            if agent_b
            else None
        ),
    }

    # Save alert to database
    try:
        save_alert(alert)
        print(f"[ALERT-SAVED] Event {event_id}: Alert saved to database")
    except Exception as e:
        print(
            f"[ALERT-ERROR] Event {event_id}: Failed to save alert - {type(e).__name__}: {str(e)[:100]}"
        )
        raise  # Re-raise so caller knows it failed

    # Record time for rate limiting
    if user_id:
        try:
            record_alert_time(user_id)
        except Exception as e:
            print(
                f"[ALERT-ERROR] Event {event_id}: Failed to record alert time - {str(e)[:100]}"
            )

    # Trigger email delivery if configured
    if "email" in alert["channels"]:
        try:
            deliver_email_alert(alert, user_prefs)
            print(f"[ALERT-EMAIL] Event {event_id}: Email delivery triggered")
        except Exception as e:
            print(
                f"[ALERT-ERROR] Event {event_id}: Email delivery failed - {type(e).__name__}: {str(e)[:100]}"
            )
            # Don't re-raise - email failure shouldn't prevent alert creation

    print(f"[ALERT-SUCCESS] Event {event_id}: Alert created and saved successfully")
    return alert
