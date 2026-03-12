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
from sqlalchemy.exc import IntegrityError
from app.modules.intelligence.application.agent_a import score_event
from app.modules.intelligence.infrastructure.models import ProcessedEvent
from app.modules.ingestion.infrastructure.models import EventORM
from app.config.db import SessionLocal  # Use synchronous session for pika consumer
from app.modules.alerting.application.alert_generator import generate_alert
from sqlalchemy import and_

# Optionally load .env for local dev
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("intelligence-consumer")

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
QUEUE_NAME = os.environ.get("RABBITMQ_QUEUE", "events")


# Dummy function for DB embeddings lookup (to be replaced with real DB call)
def get_recent_event_embeddings():
    # Return a list of embeddings from recent events (last 30 min)
    return []


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
            "title": event_orm.content.get("title", "New Alert") if event_orm.content else "New Alert",
            "content": event_orm.content or {},
        }
        
        alert = generate_alert(alert_event, user_prefs=None)
        event_id_str = str(event_orm.id)
        if alert:
            logger.info(f"[ALERT] 🚨 Generated {priority} priority alert for event {event_id_str}...")
            return alert
        else:
            logger.debug(f"[ALERT] Alert filtered (rate limit/quiet hours) for event {event_id_str}...")
            return None
    except Exception as e:
        logger.error(f"[ALERT] Failed to generate alert: {type(e).__name__}: {str(e)[:100]}")
        return None


def save_processed_event(event: dict, scores: dict):
    """Save processed event with scores to database and generate alerts for HIGH/MEDIUM priority events."""
    db = SessionLocal()
    try:
        processed_event = ProcessedEvent(
            id=int(event.get("id", 0)),  # Convert event id to integer
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
        
        # Both EventORM.id and ProcessedEvent.id are integers - no casting needed
        already_processed_ids = db.query(ProcessedEvent.id)
        
        unprocessed_events = (
            db.query(EventORM)
            .filter(~EventORM.id.in_(already_processed_ids))
            .limit(batch_size)
            .all()
        )
        
        if not unprocessed_events:
            logger.debug("[INTELLIGENCE-POLL] No unprocessed events found")
            return 0
        
        logger.info(f"[INTELLIGENCE-POLL] Processing {len(unprocessed_events)} unprocessed events")
        
        for event_orm in unprocessed_events:
            try:
                # Check again inside the loop to guard against concurrent polls
                existing = db.query(ProcessedEvent).filter(
                    ProcessedEvent.id == event_orm.id
                ).first()
                if existing:
                    logger.debug(f"[INTELLIGENCE-POLL] Skipping already-processed event {event_orm.id}")
                    continue

                event_dict = {
                    "id": str(event_orm.id),
                    "source": event_orm.source,
                    "type": event_orm.type,
                    "timestamp": event_orm.timestamp.isoformat() if event_orm.timestamp else None,
                    "content": event_orm.content or {},
                }
                
                scores = score_event(event_dict)
                priority = scores.get("priority", "LOW")
                score = scores.get("score", 0)
                
                # Save ProcessedEvent and update EventORM content in a single commit
                processed_event = ProcessedEvent(
                    id=event_orm.id,  # Store as integer (matches EventORM.id)
                    user_id=None,
                    priority=priority,
                    score=score,
                    multi_source=scores.get("multi_source", 0),
                    engagement=scores.get("engagement", 0),
                    bot=scores.get("bot", 0),
                    dedup=scores.get("dedup", 0),
                    event_data=event_dict,
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
                    f"[INTELLIGENCE] ✅ Scored event {event_orm.id} | Priority: {priority} | Score: {score:.2f}"
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
