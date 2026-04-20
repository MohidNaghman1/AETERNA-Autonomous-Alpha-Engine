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
    build_user_facing_profile,
    build_transfer_relationship_summary,
)
from app.modules.intelligence.application.trade_records import (
    upsert_trade_record_from_event,
)
from app.modules.intelligence.domain.agent_b_models import WalletTier, BehaviorCluster
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


def _persist_wallet_profile(db, wallet_address: str, profiling_output) -> None:
    """Create or update a wallet profile from Agent B output."""
    wallet_addr_lower = wallet_address.lower()
    wallet_profile = profiling_output.wallet_profile
    now = datetime.utcnow()

    entity_type = (
        profiling_output.entity_type.value
        if profiling_output.entity_type
        else profiling_output.inferred_entity_type or "unknown"
    )
    entity_name = (
        profiling_output.entity_name
        or profiling_output.inferred_entity_name
        or "New Wallet"
    )

    existing_profile = db.execute(
        select(WalletProfileORM).where(WalletProfileORM.address == wallet_addr_lower)
    ).scalar_one_or_none()

    # Keep a small baseline confidence for cold-start wallets so they do not
    # oscillate between 0.0 and 0.1 across inserts/updates.
    raw_confidence = profiling_output.confidence_score
    confidence_score = (
        float(raw_confidence) if isinstance(raw_confidence, (int, float)) else None
    )
    if confidence_score is None:
        confidence_score = 0.1
    elif confidence_score <= 0 and profiling_output.profiling_signal in {
        "unknown",
        "unverified",
    }:
        confidence_score = 0.1

    if not existing_profile:
        new_profile = WalletProfileORM(
            address=wallet_addr_lower,
            blockchain="ethereum",
            entity_type=entity_type,
            entity_name=entity_name,
            total_trades=wallet_profile.total_trades if wallet_profile else 0,
            profitable_trades=wallet_profile.profitable_trades if wallet_profile else 0,
            win_rate=wallet_profile.win_rate if wallet_profile else 0.0,
            avg_return_24h=wallet_profile.avg_return_24h if wallet_profile else 0.0,
            avg_return_7d=wallet_profile.avg_return_7d if wallet_profile else 0.0,
            best_trade_return=(
                wallet_profile.best_trade_return if wallet_profile else 0.0
            ),
            worst_trade_return=(
                wallet_profile.worst_trade_return if wallet_profile else 0.0
            ),
            behavior_cluster=(
                wallet_profile.behavior_cluster.value
                if wallet_profile and wallet_profile.behavior_cluster
                else BehaviorCluster.UNKNOWN.value
            ),
            tier=(
                wallet_profile.tier.value
                if wallet_profile and wallet_profile.tier
                else WalletTier.UNVERIFIED.value
            ),
            confidence_score=confidence_score,
            activity_frequency=(
                wallet_profile.activity_frequency if wallet_profile else "inactive"
            ),
            last_activity=now,
            first_seen=wallet_profile.first_seen if wallet_profile else now,
            preferred_tokens=wallet_profile.preferred_tokens if wallet_profile else [],
            favorite_exchanges=(
                wallet_profile.favorite_exchanges if wallet_profile else []
            ),
            favorite_dexes=wallet_profile.favorite_dexes if wallet_profile else [],
        )
        db.add(new_profile)
        logger.info(
            f"[DB PERSIST] Created profile: {wallet_addr_lower[:8]}... "
            f"(entity={entity_name}, signal={profiling_output.profiling_signal})"
        )
        return

    existing_profile.last_activity = now
    existing_profile.entity_type = entity_type or existing_profile.entity_type
    existing_profile.entity_name = entity_name or existing_profile.entity_name
    existing_profile.confidence_score = confidence_score
    existing_profile.first_seen = (
        existing_profile.first_seen or existing_profile.created_at or now
    )

    if wallet_profile:
        existing_profile.total_trades = wallet_profile.total_trades
        existing_profile.profitable_trades = wallet_profile.profitable_trades
        existing_profile.win_rate = wallet_profile.win_rate
        existing_profile.avg_return_24h = wallet_profile.avg_return_24h
        existing_profile.avg_return_7d = wallet_profile.avg_return_7d
        existing_profile.best_trade_return = wallet_profile.best_trade_return
        existing_profile.worst_trade_return = wallet_profile.worst_trade_return
        existing_profile.behavior_cluster = wallet_profile.behavior_cluster.value
        existing_profile.tier = wallet_profile.tier.value
        existing_profile.activity_frequency = wallet_profile.activity_frequency
        existing_profile.first_seen = (
            existing_profile.first_seen or wallet_profile.first_seen or now
        )
        existing_profile.preferred_tokens = wallet_profile.preferred_tokens
        existing_profile.favorite_exchanges = wallet_profile.favorite_exchanges
        existing_profile.favorite_dexes = wallet_profile.favorite_dexes

    db.add(existing_profile)


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

        content = (
            event.get("content", {}) if isinstance(event.get("content"), dict) else {}
        )
        from_address = content.get("from_address")
        to_address = content.get("to_address")
        wallet_addr = (
            event.get("wallet_address")
            or event.get("address")
            or content.get("wallet_address")
            or content.get("trader_address")
        )

        addresses_to_profile = []
        seen_addresses = set()

        if isinstance(from_address, str) and from_address:
            sender_address = from_address.lower()
            addresses_to_profile.append(("sender", sender_address))
            seen_addresses.add(sender_address)

        if isinstance(to_address, str) and to_address:
            receiver_address = to_address.lower()
            if receiver_address not in seen_addresses:
                addresses_to_profile.append(("receiver", receiver_address))
                seen_addresses.add(receiver_address)

        if not addresses_to_profile and isinstance(wallet_addr, str) and wallet_addr:
            addresses_to_profile.append(("primary", wallet_addr.lower()))

        if not addresses_to_profile:
            # No wallet to profile
            if "agent_b" not in event:
                event["agent_b"] = {
                    "profiling_signal": "N/A - no wallet address",
                    "should_boost_priority": False,
                    "confidence_score": 0.0,
                }
            return event

        config = ProfilerConfig()
        profiled_wallets = {}

        # Persist trade records (idempotent) when event is a swap/trade payload.
        # This runs in the same DB transaction scope as profile persistence.
        try:
            trade_record_action = upsert_trade_record_from_event(db, event)
            if trade_record_action != "skipped":
                logger.info(
                    f"[TRADE-RECORD] {trade_record_action.upper()} for event {event.get('id')}"
                )
        except Exception as trade_err:
            logger.error(
                f"[TRADE-RECORD] Failed to upsert trade record for {event.get('id')}: {trade_err}"
            )

        # ====================================================================
        # FIX #4 (CONSOLIDATED): Persist wallet profile to database
        # This is the PRIMARY path for profile creation (not agent_b_polling)
        # ====================================================================
        try:
            for role, address in addresses_to_profile:
                profiling_output = profile_wallet_from_event(
                    wallet_address=address,
                    event_id=str(event.get("id", "unknown")),
                    event_data=event,
                    db=db,
                    config=config,
                )
                profiling_data = profiling_output.model_dump(mode="json")
                profiling_data["user_context"] = build_user_facing_profile(
                    profiling_output,
                    role=None if role == "primary" else role,
                    event_data=event,
                )
                profiled_wallets[role] = {
                    "address": address,
                    "output": profiling_output,
                    "data": profiling_data,
                }
                _persist_wallet_profile(db, address, profiling_output)

            # Flush to ensure profile is in DB before alert generation
            db.flush()
            db.commit()

        except Exception as db_err:
            logger.error(f"[DB PERSIST] Failed to save wallet profiles: {db_err}")
            db.rollback()
            # Don't raise - allow event processing to continue

        # Attach profiling to event JSON for alert generation
        sender_profile = profiled_wallets.get("sender")
        receiver_profile = profiled_wallets.get("receiver")
        primary_profile = (
            sender_profile
            or profiled_wallets.get("primary")
            or receiver_profile
            or next(iter(profiled_wallets.values()))
        )

        relationship_summary = build_transfer_relationship_summary(
            sender_profile["output"] if sender_profile else None,
            receiver_profile["output"] if receiver_profile else None,
            event,
        )

        primary_data = deepcopy(primary_profile["data"])
        if sender_profile:
            event["agent_b_sender"] = deepcopy(sender_profile["data"])
            primary_data["sender"] = deepcopy(sender_profile["data"])
        if receiver_profile:
            event["agent_b_receiver"] = deepcopy(receiver_profile["data"])
            primary_data["receiver"] = deepcopy(receiver_profile["data"])
        if relationship_summary:
            event["agent_b_relationship"] = relationship_summary
            primary_data["relationship"] = relationship_summary

        event["agent_b"] = primary_data
        profile_signals = ", ".join(
            f"{role}={info['output'].profiling_signal}"
            for role, info in profiled_wallets.items()
        )
        logger.info(f"[AGENT B] Enriched {event.get('id')}: {profile_signals}")

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
                event_dict.get("content", {}).get("title", "New Alert")
                if event_dict.get("content")
                else "New Alert"
            ),
            "content": event_dict.get("content", {}) or {},
            "agent_b": event_dict.get("agent_b", {}),
            "agent_b_sender": event_dict.get("agent_b_sender"),
            "agent_b_receiver": event_dict.get("agent_b_receiver"),
            "agent_b_relationship": event_dict.get("agent_b_relationship"),
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
