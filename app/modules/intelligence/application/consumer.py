"""
RabbitMQ Consumer for Agent A Event Processing
"""

import json
import pika
import os
from datetime import datetime
from app.modules.intelligence.application.agent_a import score_event
from app.modules.intelligence.infrastructure.models import ProcessedEvent
from app.config.db import SessionLocal  # Use synchronous session for pika consumer
from app.modules.alerting.application.alert_generator import generate_alert

# Optionally load .env for local dev
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
QUEUE_NAME = os.environ.get("RABBITMQ_QUEUE", "events")


# Dummy function for DB embeddings lookup (to be replaced with real DB call)
def get_recent_event_embeddings():
    # Return a list of embeddings from recent events (last 30 min)
    return []


def save_processed_event(event: dict, scores: dict):
    """Save processed event with scores to database and generate alerts for HIGH/MEDIUM priority events."""
    db = SessionLocal()
    try:
        processed_event = ProcessedEvent(
            id=event.get("id"),
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

        # Generate alerts for HIGH and MEDIUM priority events
        priority = scores.get("priority", "LOW")
        if priority in ("HIGH", "MEDIUM"):
            try:
                # Prepare event data for alert generation
                alert_event = {
                    "id": event.get("id"),
                    "user_id": 0,  # System broadcast alert for all users
                    "priority": priority,
                    "score": scores.get("score", 0),
                    "title": event.get("content", {}).get(
                        "title", f"{priority} Priority Event"
                    ),
                    "summary": event.get("content", {}).get("summary", ""),
                    "text": event.get("content", {}).get("text", ""),
                }

                alert = generate_alert(alert_event, user_prefs=None)
                if alert:
                    print(
                        f"[ALERT] 🚨 Generated {priority} priority alert for event {event['id']}"
                    )
                else:
                    print(
                        f"[ALERT] ⚠️  Alert filtered out for event {event['id']} (check rate limit/quiet hours)"
                    )
            except Exception as e:
                print(
                    f"[ALERT] ❌ Failed to generate alert for event {event['id']}: {str(e)}"
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
    4. On success: ACK (remove from queue)
    5. On failure: NACK (return to queue for retry)
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


if __name__ == "__main__":
    start_consumer()
