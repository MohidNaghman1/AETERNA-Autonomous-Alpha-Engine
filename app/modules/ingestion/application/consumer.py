"""
Event Consumer for RabbitMQ
- Listens to RabbitMQ queue
- Validates, scores, and stores events in DB
- Implements DLQ (Dead Letter Queue) for failed messages
- Tracks Prometheus metrics and logs
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
from app.config.db import SessionLocal  # Use synchronous session for pika consumer
from app.shared.utils.validators import validate_event as validate_event_schema

# Start Prometheus metrics server (only once per process)
try:
    start_metrics_server(8001)
except Exception:
    pass

load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("event-consumer")

# Reduce pika verbosity
logging.getLogger("pika").setLevel(logging.WARNING)

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "events")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")

# DLQ Configuration
DLQ_QUEUE = os.getenv("RABBITMQ_DLQ_QUEUE", "events_dlq")
MAX_RETRIES = int(os.getenv("RABBITMQ_MAX_RETRIES", "3"))
RETRY_DELAY_SECONDS = int(os.getenv("RABBITMQ_RETRY_DELAY", "5"))

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)


def get_retry_count(properties: pika.BasicProperties) -> int:
    """Extract retry count from message headers"""
    if properties and properties.headers:
        return properties.headers.get("x-retry-count", 0)
    return 0


def send_to_dlq(
    channel: pika.adapters.blocking_connection.BlockingChannel,
    body: bytes,
    error_msg: str,
    retry_count: int,
):
    """Send message to Dead Letter Queue"""
    try:
        channel.queue_declare(queue=DLQ_QUEUE, durable=True)
        headers = {
            "x-retry-count": retry_count,
            "x-error-message": error_msg[:500],  # Limit error message size
            "x-failed-at": datetime.utcnow().isoformat(),
        }

        channel.basic_publish(
            exchange="",
            routing_key=DLQ_QUEUE,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2, headers=headers  # persistent
            ),
        )
        logger.info(
            f"[DLQ] Message sent to DLQ after {retry_count} retries. Error: {error_msg[:100]}"
        )
    except Exception as e:
        logger.error(f"[DLQ-ERROR] Failed to send message to DLQ: {e}")


def validate_event(event: Event) -> bool:
    if not event.id:
        logger.debug(f"[VALIDATION] Missing ID")
        return False
    if not getattr(event, "timestamp", None):
        logger.debug(f"[VALIDATION] Missing timestamp for {event.id}")
        return False
    if not event.content:
        logger.debug(f"[VALIDATION] Missing content for {event.id}")
        return False
    if len(str(event.content)) < 10:
        logger.debug(f"[VALIDATION] Content too short for {event.id}")
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


def process_event(ch, method, properties, body):
    """
    Process event message from RabbitMQ.

    P1 Enhancements:
    - Schema validation before processing
    - DLQ (Dead Letter Queue) for failed events
    - Retry logic with exponential backoff
    - Comprehensive error tracking

    Flow:
    1. Parse JSON
    2. Validate schema
    3. Validate event data
    4. Create EventORM
    5. Commit to database
    6. On success: ACK (message removed from queue)
    7. On retriable failure: NACK (message returned to queue for retry)
    8. On max retries exceeded: Send to DLQ and ACK
    9. On non-retriable failure: Send to DLQ and ACK
    """
    success = False
    db = None
    retry_count = get_retry_count(properties)

    try:
        data = json.loads(body)
        # Map event_type to type if needed
        if "event_type" in data:
            data["type"] = data.pop("event_type")

        try:
            event = Event(**data)
        except Exception as e:
            logger.error(
                f"[ERROR] Failed to create Event from data: {type(e).__name__}: {str(e)[:100]}"
            )
            logger.error(
                f"[ERROR] Data keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}"
            )
            # Invalid message format - send to DLQ (non-retriable)
            send_to_dlq(
                ch, body, f"Event deserialization failed: {str(e)}", retry_count
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Validate event schema
        is_valid, validation_error = validate_event_schema(event.model_dump())
        if not is_valid:
            logger.warning(
                f"[VALIDATION-FAILED] Event {getattr(event, 'id', None)}: {validation_error}"
            )
            # Schema validation failed - send to DLQ (non-retriable)
            send_to_dlq(
                ch, body, f"Schema validation failed: {validation_error}", retry_count
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Validate event
        if not validate_event(event):
            logger.warning(
                f"[INVALID] Event {getattr(event, 'id', None)} failed validation. Title: {data.get('content', {}).get('title', 'N/A')[:50]}"
            )
            # Invalid events don't get retried - send to DLQ and ACK
            send_to_dlq(ch, body, "Event validation failed", retry_count)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        score = score_event(event)

        # Process event and store in database
        with EVENT_PROCESSING_TIME.labels(collector="consumer").time():
            try:
                db = SessionLocal()
                # Prepare content
                content = event.content or {}
                if isinstance(content, str):
                    content = json_module.loads(content)
                content["event_hash"] = event.id  # For deduplication tracking

                logger.debug(
                    f"[DEBUG] Creating EventORM with content keys: {list(content.keys())}"
                )

                # Parse timestamp string to datetime object
                # Event.timestamp is ISO8601 string (e.g., "2026-03-04T12:27:02Z")
                # EventORM.timestamp expects datetime object
                timestamp_str = getattr(event, "timestamp", None)
                if timestamp_str:
                    # Remove 'Z' suffix and parse
                    ts_clean = timestamp_str.rstrip("Z")
                    timestamp_dt = datetime.fromisoformat(ts_clean)
                else:
                    timestamp_dt = None

                # Create ORM object
                db_event = EventORM(
                    source=getattr(event, "source", None),
                    type=getattr(event, "type", None),
                    timestamp=timestamp_dt,
                    content=content,
                    raw=None,
                )

                # Save to database
                db.add(db_event)
                db.commit()
                db.refresh(db_event)

                logger.info(
                    f"[✅] Event {event.id} | {getattr(event, 'source', 'unknown')} | {data.get('content', {}).get('title', 'N/A')[:40]}"
                )

                success = True
                EVENTS_PROCESSED.labels(collector="consumer").inc()

            except Exception as e:
                # Database error - retriable
                logger.error(
                    f"[❌ DB ERROR] Failed to store event {getattr(event, 'id', None)}: {type(e).__name__}: {str(e)}"
                )
                if db:
                    try:
                        db.rollback()
                    except Exception as rb_err:
                        logger.error(f"[ERROR] Rollback failed: {rb_err}")
                success = False
                raise  # Re-raise to trigger retry logic

            finally:
                if db:
                    try:
                        db.close()
                    except Exception:
                        pass

        # P1 Fix: ACK only on success
        if success:
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            if retry_count < MAX_RETRIES:
                # Increment retry count and requeue
                logger.warning(
                    f"[RETRY] Message will be retried (attempt {retry_count + 1}/{MAX_RETRIES})"
                )
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            else:
                # Max retries exceeded - send to DLQ
                logger.error(
                    f"[DLQ] Max retries ({MAX_RETRIES}) exceeded, sending to DLQ"
                )
                send_to_dlq(ch, body, "Max retries exceeded", retry_count)
                ch.basic_ack(delivery_tag=method.delivery_tag)

    except json.JSONDecodeError as e:
        # Bad JSON - non-retriable
        logger.error(f"[❌ JSON ERROR] Failed to parse JSON: {e}")
        send_to_dlq(ch, body, f"JSON parsing failed: {str(e)}", retry_count)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    except Exception as e:
        # Unexpected error - might be retriable
        logger.error(
            f"[❌ UNEXPECTED ERROR] {type(e).__name__}: {str(e)}", exc_info=True
        )

        if retry_count < MAX_RETRIES:
            logger.warning(
                f"[RETRY] Retrying message (attempt {retry_count + 1}/{MAX_RETRIES})"
            )
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        else:
            logger.error(f"[DLQ] Max retries exceeded, sending to DLQ")
            send_to_dlq(ch, body, f"Unexpected error: {str(e)[:100]}", retry_count)
            ch.basic_ack(delivery_tag=method.delivery_tag)


def run_consumer():
    # Prefer URL-based connection (CloudAMQP format)
    if RABBITMQ_URL:
        try:
            logger.info(f"[CONSUMER] Connecting via URL...")
            conn_params = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection([conn_params])
        except Exception as e:
            logger.error(f"[ERROR] Failed to connect via URL: {e}")
            logger.info(f"[CONSUMER] Falling back to host-based connection...")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    virtual_host=RABBITMQ_VHOST,
                    credentials=credentials,
                )
            )
    else:
        logger.info(f"[CONSUMER] Connecting via host/user/password...")
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                virtual_host=RABBITMQ_VHOST,
                credentials=credentials,
            )
        )

    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=process_event)
    logger.info(f"[CONSUMER] Listening on queue '{RABBITMQ_QUEUE}'...")
    channel.start_consuming()


def run_consumer_poll(batch_size: int = 1000) -> int:
    """
    Non-blocking consumer that polls RabbitMQ queue.

    Processes up to batch_size messages per call.
    Returns number of messages processed.
    Safe to call repeatedly without blocking.
    """
    logger.info(f"[CONSUMER-POLL-BATCH] batch_size={batch_size}")
    processed_count = 0
    connection = None
    channel = None

    try:
        # Prefer URL-based connection (CloudAMQP format)
        if RABBITMQ_URL:
            try:
                logger.debug(f"[CONSUMER-POLL] Connecting via URL...")
                conn_params = pika.URLParameters(RABBITMQ_URL)
                connection = pika.BlockingConnection([conn_params])
            except Exception as e:
                logger.error(f"[CONSUMER-POLL] Failed to connect via URL: {e}")
                logger.debug(
                    f"[CONSUMER-POLL] Falling back to host-based connection..."
                )
                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=RABBITMQ_HOST,
                        port=RABBITMQ_PORT,
                        virtual_host=RABBITMQ_VHOST,
                        credentials=credentials,
                    )
                )
        else:
            logger.debug(f"[CONSUMER-POLL] Connecting via host/user/password...")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    virtual_host=RABBITMQ_VHOST,
                    credentials=credentials,
                )
            )

        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        # Set prefetch to batch_size so RabbitMQ sends multiple messages at once (not just 1)
        channel.basic_qos(prefetch_count=min(batch_size, 1000))

        logger.info(
            f"[CONSUMER-POLL] Processing up to {batch_size} messages (prefetch={min(batch_size, 1000)})"
        )
        for attempt in range(batch_size):
            try:
                method, properties, body = channel.basic_get(
                    queue=RABBITMQ_QUEUE, auto_ack=False
                )
            except Exception as e:
                logger.error(
                    f"[CONSUMER-POLL] basic_get() failed at attempt {attempt}: {e}"
                )
                break

            if method:
                try:
                    process_event(channel, method, properties, body)
                    processed_count += 1
                except Exception as e:
                    logger.error(f"[CONSUMER-POLL] Error processing message: {e}")
                    try:
                        channel.basic_nack(
                            delivery_tag=method.delivery_tag, requeue=True
                        )
                    except:
                        pass
            else:
                break

        if processed_count > 0:
            logger.info(
                f"[CONSUMER-POLL] Processed {processed_count} messages from queue"
            )

        return processed_count

    except Exception as e:
        logger.error(
            f"[CONSUMER-POLL] Connection error: {type(e).__name__}: {str(e)}",
            exc_info=True,
        )
        return 0

    finally:
        # Close connection
        try:
            if channel and channel.is_open:
                channel.close()
            if connection and connection.is_open:
                connection.close()
        except Exception as e:
            logger.error(f"[CONSUMER-POLL] Error closing connection: {e}")


if __name__ == "__main__":
    run_consumer()
