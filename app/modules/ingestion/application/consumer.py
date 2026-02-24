"""
Event Consumer for RabbitMQ
- Listens to RabbitMQ queue
- Validates, scores, and stores events in DB
- Tracks Prometheus metrics and logs
"""

import pika
import os
import json
import logging
from dotenv import load_dotenv
from app.modules.ingestion.domain.models import Event
from app.shared.utils.monitoring import EVENTS_PROCESSED, EVENT_PROCESSING_TIME, start_metrics_server
from app.modules.ingestion.infrastructure.models import EventORM
from app.config.db import AsyncSessionLocal as SessionLocal

# Start Prometheus metrics server (only once per process)
try:
    start_metrics_server(8001)
except Exception:
    pass

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("event-consumer")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "events")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)


def validate_event(event: Event) -> bool:
    if not event.id or not getattr(event, 'timestamp', None) or not event.content:
        return False
    if len(str(event.content)) < 10:
        return False
    return True


def score_event(event: Event) -> int:
    score = 0
    if getattr(event, 'entities', None):
        score += 10 * len(event.entities)
    if getattr(event, 'type', None) == "news":
        score += 10
    if getattr(event, 'type', None) == "price":
        score += 5
    return score


def process_event(ch, method, properties, body):
    try:
        data = json.loads(body)
        # Before creating EventORM
        if 'event_type' in data:
            data['type'] = data.pop('event_type')
        event = Event(**data)
        if not validate_event(event):
            logger.warning(f"[INVALID] Event {getattr(event, 'id', None)} failed validation.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        score = score_event(event)
        with EVENT_PROCESSING_TIME.labels(collector="consumer").time():
            try:
                db = SessionLocal()
                db_event = EventORM(
                    id=event.id,
                    source=getattr(event, 'source', None),
                    type=getattr(event, 'type', None),
                    timestamp=getattr(event, 'timestamp', None),
                    content=event.content,
                    raw=None  # or event.raw if available
                )
                db.add(db_event)
                db.commit()
                db.refresh(db_event)
                logger.info(f"[PROCESSED] Event {event.id} | Type: {getattr(event, 'type', None)} | Entities: {getattr(event, 'entities', None)} | Score: {score} | Stored in DB.")
            except Exception as e:
                logger.error(f"[ERROR] Failed to store event {getattr(event, 'id', None)}: {e}", exc_info=True)
            finally:
                try:
                    db.close()
                except Exception:
                    pass
        EVENTS_PROCESSED.labels(collector="consumer").inc()
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"[ERROR] Failed to process event: {e}", exc_info=True)
        ch.basic_ack(delivery_tag=method.delivery_tag)


def run_consumer():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=5672,
        credentials=credentials
    ))
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=process_event)
    logger.info(f"[CONSUMER] Listening on queue '{RABBITMQ_QUEUE}'...")
    channel.start_consuming()

if __name__ == "__main__":
    run_consumer()