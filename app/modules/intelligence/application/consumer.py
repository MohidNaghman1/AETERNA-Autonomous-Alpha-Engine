"""
Consumer for Agent A Event Processing (Intelligence Pipeline)
- Reads events from EventORM table
- Scores events using Agent A
- Creates ProcessedEvent records
- Generates HIGH/MEDIUM priority alerts
"""

import json
import pika
import os
import logging
from datetime import datetime
from copy import deepcopy
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, cast, String
from app.modules.intelligence.application.agent_a import score_event
from app.modules.intelligence.application.agent_b import (
    profile_wallet_from_event,
    ProfilerConfig,
)
from app.modules.intelligence.infrastructure.models import (
    ProcessedEvent,
    WalletProfileORM,
)
from app.modules.ingestion.infrastructure.models import EventORM
from sqlalchemy import select
from app.config.db import SessionLocal  # Use synchronous session for pika consumer
from app.modules.alerting.application.alert_generator import generate_alert

# Optionally load .env for local dev
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("intelligence-consumer")

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
QUEUE_NAME = os.environ.get("RABBITMQ_QUEUE", "events")


# Dummy function for DB embeddings lookup (to be replaced with real DB call)
def get_recent_event_embeddings():
    # Return a list of embeddings from recent events (last 30 min)
    return []


def enrich_event_with_agent_b(event: dict) -> dict:
    """
    FIX #1 + #4: Enrich event with Agent B profiling AND persist wallet profile to DB.

    This function:
    1. Profiles wallet(s) from the event
    2. Creates/updates WalletProfileORM record in database (PRIMARY path for persistence)
    3. Attaches profiling data to event JSON for alert generation

    Handles both cases:
    - Wallets with trade history → Profile from trades
    - New wallets (no trades) → Profile from inferred entity type (e.g., "Whale")

    Args:
        event: Event dict that may contain wallet addresses

    Returns:
        Modified event dict with agent_b profiling added (or original if error/no profiling needed)
    """
    db = SessionLocal()
    try:
        event_source = event.get("source", "").lower()

        # Only profile on-chain events
        if event_source != "ethereum":
            # Mark non-wallet events as processed without profiling
            if "agent_b" not in event:
                event["agent_b"] = {
                    "profiling_signal": "N/A - non-wallet event",
                    "should_boost_priority": False,
                    "confidence_score": 0.0,
                }
            return event

        # Extract wallet addresses (both sender and receiver for transfers)
        content = (
            event.get("content", {}) if isinstance(event.get("content"), dict) else {}
        )

        # Try all possible wallet address fields
        wallet_addr = (
            event.get("wallet_address")
            or event.get("address")
            or content.get("from_address")
            or content.get("to_address")
        )

        if not wallet_addr:
            # No wallet to profile
            if "agent_b" not in event:
                event["agent_b"] = {
                    "profiling_signal": "N/A - no wallet address",
                    "should_boost_priority": False,
                    "confidence_score": 0.0,
                }
            return event

        wallet_addr_lower = wallet_addr.lower()

        # Run Agent B profiling
        config = ProfilerConfig()
        profiling_output = profile_wallet_from_event(
            wallet_address=wallet_addr,
            event_id=str(event.get("id", "unknown")),
            event_data=event,
            db=db,
            config=config,
        )

        # ====================================================================
        # FIX #4 (CONSOLIDATED): Persist wallet profile to database
        # This is the PRIMARY path for profile creation (not agent_b_polling)
        # ====================================================================
        try:
            wp = profiling_output.wallet_profile  # Could be None if no trades

            # Check if profile already exists
            existing_profile = db.execute(
                select(WalletProfileORM).where(
                    WalletProfileORM.address == wallet_addr_lower
                )
            ).scalar_one_or_none()

            if not existing_profile:
                # Create new profile for ANY wallet we see (not just those with history/inference)
                # This allows tracking of all wallets from first event, avoiding "unknown" blind spots
                new_profile = WalletProfileORM(
                    address=wallet_addr_lower,
                    blockchain="ethereum",
                    entity_type=profiling_output.inferred_entity_type or "unknown",
                    entity_name=profiling_output.inferred_entity_name or "New Wallet",
                    total_trades=wp.total_trades if wp else 0,
                    profitable_trades=wp.profitable_trades if wp else 0,
                    win_rate=wp.win_rate if wp else 0.0,
                    behavior_cluster=str(wp.behavior_cluster) if wp else "UNKNOWN",
                    tier=str(wp.tier) if wp else "UNVERIFIED",
                    confidence_score=profiling_output.confidence_score or 0.1,
                    activity_frequency="new",
                    preferred_tokens=wp.preferred_tokens if wp else [],
                    last_activity=datetime.utcnow(),
                )
                db.add(new_profile)
                reason = "Trades" if wp else ("Inference" if profiling_output.inferred_entity_name else "Cold-Start")
                logger.info(
                    f"[DB PERSIST] Created profile: {wallet_addr_lower[:8]}... "
                    f"(entity={profiling_output.inferred_entity_name or 'unknown'}, signal={profiling_output.profiling_signal}, reason={reason})"
                )

            elif existing_profile and (wp or profiling_output.inferred_entity_name):
                # Update existing profile if we have new/better information (trades or inference)
                existing_profile.last_activity = datetime.utcnow()
                if wp:
                    # Update trade stats if available
                    existing_profile.total_trades = wp.total_trades
                    existing_profile.profitable_trades = wp.profitable_trades
                    existing_profile.win_rate = wp.win_rate
                    existing_profile.behavior_cluster = str(wp.behavior_cluster)
                    existing_profile.tier = str(wp.tier)
                    existing_profile.confidence_score = profiling_output.confidence_score
                    existing_profile.preferred_tokens = wp.preferred_tokens
                if profiling_output.inferred_entity_name:
                    # Update entity info if inferred
                    existing_profile.entity_type = profiling_output.inferred_entity_type or existing_profile.entity_type
                    existing_profile.entity_name = profiling_output.inferred_entity_name or existing_profile.entity_name
                db.add(existing_profile)
                logger.debug(
                    f"[DB PERSIST] Updated profile: {wallet_addr_lower[:8]}... "
                    f"(tier={existing_profile.tier}, trades={existing_profile.total_trades})"
                )

            # Flush to ensure profile is in DB before alert generation
            db.flush()
            db.commit()

        except Exception as db_err:
            logger.error(
                f"[DB PERSIST] Failed to save profile for {wallet_addr_lower}: {db_err}"
            )
            db.rollback()
            # Don't raise - allow event processing to continue

        # Attach profiling to event JSON for alert generation
        event["agent_b"] = profiling_output.model_dump(mode="json")
        logger.info(
            f"[AGENT B] ✓ Enriched {event.get('id')}: {profiling_output.profiling_signal} "
            f"(boost={profiling_output.should_boost_priority})"
        )

    except Exception as e:
        logger.error(
            f"[AGENT B] ✗ Error enriching event {event.get('id')}: {e}", exc_info=True
        )
        # Return event as-is if Agent B fails; don't block the pipeline
        if "agent_b" not in event:
            event["agent_b"] = {
                "profiling_signal": "error",
                "should_boost_priority": False,
                "confidence_score": 0.0,
            }
    finally:
        try:
            db.close()
        except:
            pass

    return event


def _generate_alert_for_scored_event(event_orm, event_dict, priority, score):
    """
    Helper function to generate alerts for HIGH/MEDIUM priority events.

    Args:
        event_orm: EventORM instance (with content field)
        event_dict: Dict representation of event
        priority: Priority level (HIGH, MEDIUM, LOW)
        score: Numerical score

    Returns:
        Generated alert dict or None if filtered
    """
    if priority not in ("HIGH", "MEDIUM"):
        return None

    try:
        alert_event = {
            "id": str(event_orm.id),
            "user_id": None,  # System broadcast
            "priority": priority,
            "score": score,
            "title": (
                event_orm.content.get("title", "New Alert")
                if event_orm.content
                else "New Alert"
            ),
            "content": event_orm.content or {},
        }

        alert = generate_alert(alert_event, user_prefs=None)
        event_id_str = str(event_orm.id)
        if alert:
            logger.info(
                f"[ALERT] Generated {priority} priority alert for event {event_id_str}"
            )
            return alert
        else:
            logger.debug(
                f"[ALERT] Alert filtered (rate limit/quiet hours) for event {event_id_str}..."
            )
            return None
    except Exception as e:
        logger.error(
            f"[ALERT] Failed to generate alert: {type(e).__name__}: {str(e)[:100]}"
        )
        return None


def save_processed_event(event: dict, scores: dict):
    """Save processed event with scores to database and generate alerts for HIGH/MEDIUM priority events."""
    db = SessionLocal()
    try:
        processed_event = ProcessedEvent(
            id=str(event.get("id", "")),  # Store event id as string (matches DB schema)
            user_id=event.get("user_id"),
            priority=scores.get("priority", "LOW"),
            score=scores.get("score", 0),
            multi_source=scores.get("multi_source", 0),
            engagement=scores.get("engagement", 0),
            bot=scores.get("bot", 0),
            dedup=scores.get("dedup", 0),
            event_data=event,
            timestamp=datetime.utcnow(),
        )
        db.add(processed_event)
        db.commit()
        db.refresh(processed_event)
        print(
            f"[DB] ✅ Saved processed event {event['id']} | Priority: {scores.get('priority')} | Score: {scores.get('score'):.2f}"
        )

        return processed_event
    except Exception as e:
        db.rollback()
        print(f"[DB] ❌ Failed to save processed event {event.get('id')}: {str(e)}")
        return None
    finally:
        db.close()


def process_event(ch, method, properties, body):
    """
    Process event message from RabbitMQ queue.

    P1 Fix: Only ACK message after successful database commit.
    If processing fails, message is NACKed and returned to queue for retry.

    Flow:
    1. Parse JSON message
    2. Score event using Agent A
    3. Save to database
    4. Generate alerts if HIGH/MEDIUM priority
    5. On success: ACK (remove from queue)
    6. On failure: NACK (return to queue for retry)
    """
    try:
        event = json.loads(body)
        db_embeddings = get_recent_event_embeddings()
        result = score_event(event, db_embeddings)
        event.update(result)

        # =====================================================================
        # RUN AGENT B BEFORE SAVING/ALERTING (prevents race condition)
        # =====================================================================
        event = enrich_event_with_agent_b(event)
        # =====================================================================

        # Save to DB (raises exception on failure)
        processed = save_processed_event(event, result)

        if processed:
            # P1 Fix: Only ACK after successful DB save
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(
                f"[✅ PROCESSED] Event {event.get('id', 'N/A')} | Priority: {result.get('priority')} | Score: {result.get('score'):.2f}"
            )
        else:
            # DB save failed - NACK to retry
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            print(
                f"[⚠️  NACKED] Event {event.get('id', 'N/A')} - Database save failed, returning to queue"
            )

    except json.JSONDecodeError as e:
        # Bad JSON - NACK without requeue (permanent failure)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        print(f"[❌ ERROR] Failed to parse JSON: {e}")

    except Exception as e:
        # Other errors - NACK with requeue (might recover)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        print(f"[❌ ERROR] Error processing event: {type(e).__name__}: {e}")


def start_consumer():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    print(f"[*] Waiting for messages in '{QUEUE_NAME}'. To exit press CTRL+C")
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_event)
    channel.start_consuming()


def run_intelligence_poll(batch_size: int = 50) -> int:
    processed_count = 0
    db = None

    try:
        db = SessionLocal()

        # EventORM.id is Integer, ProcessedEvent.id is String - need to cast for comparison
        already_processed_ids = db.query(ProcessedEvent.id)

        unprocessed_events = (
            db.query(EventORM)
            .filter(~cast(EventORM.id, String).in_(already_processed_ids))
            .limit(batch_size)
            .all()
        )

        if not unprocessed_events:
            logger.debug("[INTELLIGENCE-POLL] No unprocessed events found")
            return 0

        logger.info(
            f"[INTELLIGENCE-POLL] Processing {len(unprocessed_events)} unprocessed events"
        )

        for event_orm in unprocessed_events:
            try:
                # Check again inside the loop to guard against concurrent polls
                # Cast integer event_orm.id to string to match ProcessedEvent.id column type
                existing = (
                    db.query(ProcessedEvent)
                    .filter(ProcessedEvent.id == cast(event_orm.id, String))
                    .first()
                )
                if existing:
                    logger.debug(
                        f"[INTELLIGENCE-POLL] Skipping already-processed event {event_orm.id}"
                    )
                    continue

                event_dict = {
                    "id": str(event_orm.id),
                    "source": event_orm.source,
                    "type": event_orm.type,
                    "timestamp": (
                        event_orm.timestamp.isoformat() if event_orm.timestamp else None
                    ),
                    "content": event_orm.content or {},
                }

                scores = score_event(event_dict)
                priority = scores.get("priority", "LOW")
                score = scores.get("score", 0)

                # =====================================================================
                # AGENT B ENRICHMENT: Persist wallet profiles + attach profiling data
                # =====================================================================
                event_dict = enrich_event_with_agent_b(event_dict)
                # =====================================================================

                # Save ProcessedEvent and update EventORM content in a single commit
                processed_event = ProcessedEvent(
                    id=str(event_orm.id),  # Store as string (matches DB schema)
                    user_id=None,
                    priority=priority,
                    score=score,
                    multi_source=scores.get("multi_source", 0),
                    engagement=scores.get("engagement", 0),
                    bot=scores.get("bot", 0),
                    dedup=scores.get("dedup", 0),
                    event_data=event_dict,  # Now includes agent_b profiling after enrichment
                    timestamp=datetime.utcnow(),
                )
                db.add(processed_event)

                # Update priority in content in the same commit
                # IMPORTANT: Copy dict before mutation - SQLAlchemy may not detect in-place mutations
                if event_orm.content is None:
                    event_orm.content = {}
                updated_content = dict(event_orm.content)
                updated_content["priority"] = priority
                event_orm.content = updated_content
                db.add(event_orm)

                db.commit()  # Single commit for both changes
                db.refresh(processed_event)

                logger.info(
                    f"[INTELLIGENCE-POLL] ✅ Event {event_orm.id} | "
                    f"Priority: {priority} | Score: {score:.2f} | "
                    f"Agent B: {'Enriched+Persisted' if event_dict.get('agent_b') else 'N/A'}"
                )

                _generate_alert_for_scored_event(event_orm, event_dict, priority, score)
                processed_count += 1

            except IntegrityError as e:
                # Another concurrent poll inserted this event between our check and commit
                logger.warning(
                    f"[INTELLIGENCE] ⚠️ Concurrent insert detected for event {event_orm.id} "
                    f"(another poll processed it first)"
                )
                db.rollback()
                # Don't increment processed_count since this poll didn't actually process it
                continue

            except Exception as e:
                logger.error(
                    f"[INTELLIGENCE] ❌ Failed to process event {event_orm.id}: "
                    f"{type(e).__name__}: {str(e)[:100]}"
                )
                db.rollback()
                continue

        return processed_count

    except Exception as e:
        logger.error(f"[INTELLIGENCE-POLL] Error: {type(e).__name__}: {str(e)[:200]}")
        return 0
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    start_consumer()
