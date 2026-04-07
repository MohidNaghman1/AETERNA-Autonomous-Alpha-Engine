"""
Event Consumer for RabbitMQ - OPTIMIZED
- Batch DB commits (bulk insert instead of one-by-one)
- Fixed retry loop (NACK requeue=True → was causing infinite loops)
- Connection pooling via single shared session per batch
- Heartbeat to keep RabbitMQ connection alive during slow processing
"""

import pika
import os
import json as json_module
import json
import logging
from dotenv import load_dotenv
from datetime import datetime
from app.modules.ingestion.domain.models import Event
from app.shared.utils.monitoring import (
    EVENTS_PROCESSED,
    EVENT_PROCESSING_TIME,
    start_metrics_server,
)
from app.modules.ingestion.infrastructure.models import EventORM
from app.config.db import SessionLocal
from app.shared.utils.validators import validate_event as validate_event_schema

try:
    start_metrics_server(8001)
except Exception:
    pass

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("event-consumer")
logging.getLogger("pika").setLevel(logging.WARNING)

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "events")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")

DLQ_QUEUE = os.getenv("RABBITMQ_DLQ_QUEUE", "events_dlq")
MAX_RETRIES = int(os.getenv("RABBITMQ_MAX_RETRIES", "3"))

# Batch settings - tune these for your DB throughput
BATCH_SIZE = int(os.getenv("CONSUMER_BATCH_SIZE", "100"))

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)

# Module-level DLQ channel (reused, not recreated per message)
_dlq_declared = False


def get_retry_count(properties: pika.BasicProperties) -> int:
    if properties and properties.headers:
        return properties.headers.get("x-retry-count", 0)
    return 0


def send_to_dlq(channel, body: bytes, error_msg: str, retry_count: int):
    global _dlq_declared
    try:
        if not _dlq_declared:
            channel.queue_declare(queue=DLQ_QUEUE, durable=True)
            _dlq_declared = True
        headers = {
            "x-retry-count": retry_count,
            "x-error-message": error_msg[:500],
            "x-failed-at": datetime.utcnow().isoformat(),
        }
        channel.basic_publish(
            exchange="",
            routing_key=DLQ_QUEUE,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2, headers=headers),
        )
    except Exception as e:
        logger.error(f"[DLQ-ERROR] Failed to send to DLQ: {e}")


def validate_event(event: Event) -> bool:
    if not event.id:
        return False
    if not getattr(event, "timestamp", None):
        return False
    if not event.content:
        return False
    if len(str(event.content)) < 10:
        return False
    return True


def score_event(event: Event) -> int:
    score = 0
    if getattr(event, "entities", None):
        score += 10 * len(event.entities)
    if getattr(event, "type", None) == "news":
        score += 10
    if getattr(event, "type", None) == "price":
        score += 5
    return score


def parse_event(body: bytes):
    """
    Parse and validate a raw message body.
    Returns (EventORM, delivery_tag) or raises.
    Returns None if message should be DLQ'd (non-retriable).
    """
    data = json.loads(body)  # raises JSONDecodeError if bad
    if "event_type" in data:
        data["type"] = data.pop("event_type")

    try:
        event = Event(**data)
    except Exception as e:
        raise ValueError(f"Event deserialization failed: {e}") from e

    is_valid, validation_error = validate_event_schema(event.model_dump())
    if not is_valid:
        raise ValueError(f"Schema validation failed: {validation_error}")

    if not validate_event(event):
        raise ValueError("Event data validation failed")

    # Parse timestamp
    timestamp_str = getattr(event, "timestamp", None)
    if timestamp_str:
        timestamp_dt = datetime.fromisoformat(timestamp_str.rstrip("Z"))
    else:
        timestamp_dt = None

    content = event.content or {}
    if isinstance(content, str):
        content = json_module.loads(content)
    content["event_hash"] = event.id

    return EventORM(
        source=getattr(event, "source", None),
        type=getattr(event, "type", None),
        timestamp=timestamp_dt,
        content=content,
        raw=None,
    )


# ─── Batch state ──────────────────────────────────────────────────────────────
_batch_orms = []        # EventORM objects ready to bulk-insert
_batch_tags = []        # delivery tags to ACK on success
_batch_dlq = []         # (body, error, retry_count) to DLQ on flush
_batch_dlq_tags = []    # delivery tags for DLQ messages (ACK after DLQ send)


def flush_batch(channel):
    """Bulk-insert the current batch then ACK/DLQ all messages in it."""
    global _batch_orms, _batch_tags, _batch_dlq, _batch_dlq_tags

    # 1. Bulk insert valid events
    if _batch_orms:
        db = None
        try:
            db = SessionLocal()
            db.bulk_save_objects(_batch_orms)
            db.commit()
            EVENTS_PROCESSED.labels(collector="consumer").inc(len(_batch_orms))
            logger.info(f"[BATCH] ✅ Committed {len(_batch_orms)} events")

            # ACK all successfully committed messages
            for tag in _batch_tags:
                try:
                    channel.basic_ack(delivery_tag=tag)
                except Exception as e:
                    logger.error(f"[BATCH] ACK failed for tag {tag}: {e}")

        except Exception as e:
            logger.error(f"[BATCH] ❌ DB bulk insert failed: {e}")
            if db:
                try:
                    db.rollback()
                except Exception:
                    pass
            # On DB failure: NACK without requeue → go to DLQ via RabbitMQ policy
            # Do NOT requeue=True — that causes infinite loops
            for tag in _batch_tags:
                try:
                    channel.basic_nack(delivery_tag=tag, requeue=False)
                except Exception:
                    pass
        finally:
            if db:
                try:
                    db.close()
                except Exception:
                    pass

    # 2. Send invalid/unparseable messages to DLQ and ACK them
    for body, error_msg, retry_count in _batch_dlq:
        send_to_dlq(channel, body, error_msg, retry_count)
    for tag in _batch_dlq_tags:
        try:
            channel.basic_ack(delivery_tag=tag)
        except Exception as e:
            logger.error(f"[BATCH] DLQ ACK failed for tag {tag}: {e}")

    # Reset batch state
    _batch_orms.clear()
    _batch_tags.clear()
    _batch_dlq.clear()
    _batch_dlq_tags.clear()


def process_event(ch, method, properties, body):
    """
    Callback for each RabbitMQ message.
    Parses and validates the message, then adds it to the current batch.
    Flushes the batch to DB every BATCH_SIZE messages.
    """
    global _batch_orms, _batch_tags, _batch_dlq, _batch_dlq_tags

    retry_count = get_retry_count(properties)

    try:
        orm = parse_event(body)
        _batch_orms.append(orm)
        _batch_tags.append(method.delivery_tag)

    except json.JSONDecodeError as e:
        # Unparseable JSON — DLQ immediately, never retry
        logger.error(f"[JSON ERROR] {e}")
        _batch_dlq.append((body, f"JSON parsing failed: {e}", retry_count))
        _batch_dlq_tags.append(method.delivery_tag)

    except ValueError as e:
        # Validation failure — DLQ immediately, never retry
        logger.warning(f"[VALIDATION] {e}")
        _batch_dlq.append((body, str(e), retry_count))
        _batch_dlq_tags.append(method.delivery_tag)

    except Exception as e:
        # Unexpected parse error — DLQ
        logger.error(f"[PARSE ERROR] {type(e).__name__}: {e}")
        _batch_dlq.append((body, f"Unexpected parse error: {e}", retry_count))
        _batch_dlq_tags.append(method.delivery_tag)

    # Flush when batch is full
    if len(_batch_orms) + len(_batch_dlq_tags) >= BATCH_SIZE:
        flush_batch(ch)


def run_consumer():
    """
    Blocking RabbitMQ consumer with batch DB commits.
    Auto-flushes every BATCH_SIZE messages.
    Heartbeat keeps connection alive during slow DB commits.
    """
    global _batch_orms, _batch_tags, _batch_dlq, _batch_dlq_tags

    # Reset batch state on each (re)start
    _batch_orms.clear()
    _batch_tags.clear()
    _batch_dlq.clear()
    _batch_dlq_tags.clear()

    if RABBITMQ_URL:
        params = pika.URLParameters(RABBITMQ_URL)
    else:
        params = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            virtual_host=RABBITMQ_VHOST,
            credentials=credentials,
        )

    # Heartbeat keeps connection alive when DB commits are slow
    params.heartbeat = 600
    params.blocked_connection_timeout = 300

    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

    # prefetch = BATCH_SIZE so RabbitMQ sends exactly one batch worth at a time
    channel.basic_qos(prefetch_count=BATCH_SIZE)
    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=process_event)

    logger.info(
        f"[CONSUMER] Listening on '{RABBITMQ_QUEUE}' | batch_size={BATCH_SIZE} | heartbeat=600s"
    )

    try:
        channel.start_consuming()
    except Exception:
        # Flush any remaining buffered messages before dying
        if _batch_orms or _batch_dlq:
            logger.info(f"[CONSUMER] Flushing {len(_batch_orms)} buffered events before exit...")
            try:
                flush_batch(channel)
            except Exception as fe:
                logger.error(f"[CONSUMER] Final flush failed: {fe}")
        raise


if __name__ == "__main__":
    run_consumer()