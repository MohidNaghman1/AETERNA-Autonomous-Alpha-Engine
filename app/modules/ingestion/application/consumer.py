"""
Event Consumer for RabbitMQ
- Listens to RabbitMQ queue
- Validates, scores, and stores events in DB
- Tracks Prometheus metrics and logs
"""

import pika
import os
import json as json_module
import json
import logging
from dotenv import load_dotenv
from app.modules.ingestion.domain.models import Event
from app.shared.utils.monitoring import EVENTS_PROCESSED, EVENT_PROCESSING_TIME, start_metrics_server
from app.modules.ingestion.infrastructure.models import EventORM
from app.config.db import SessionLocal  # Use synchronous session for pika consumer

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
    """
    Process event message from RabbitMQ.
    
    P1 Fix: Only ACK message after successful database commit.
    If database commit fails, message is NACKed and returned to queue.
    
    Flow:
    1. Parse JSON
    2. Validate event
    3. Create EventORM
    4. Commit to database
    5. On success: ACK (message removed from queue)
    6. On failure: NACK (message returned to queue for retry)
    """
    success = False
    db = None
    
    try:
        data = json.loads(body)
        # Map event_type to type if needed
        if 'event_type' in data:
            data['type'] = data.pop('event_type')
        
        event = Event(**data)
        
        # Validate event
        if not validate_event(event):
            logger.warning(f"[INVALID] Event {getattr(event, 'id', None)} failed validation.")
            # Invalid events don't get retried - ACK and discard
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
                content['event_hash'] = event.id  # For deduplication tracking
                
                logger.debug(f"[DEBUG] Creating EventORM with content keys: {list(content.keys())}")
                
                # Create ORM object
                db_event = EventORM(
                    source=getattr(event, 'source', None),
                    type=getattr(event, 'type', None),
                    timestamp=getattr(event, 'timestamp', None),
                    content=content,
                    raw=None
                )
                
                # Save to database
                db.add(db_event)
                db.commit()
                db.refresh(db_event)
                
                logger.info(f"[✅ PROCESSED] Event {event.id} (DB ID: {db_event.id}) | Type: {getattr(event, 'type', None)} | Score: {score}")
                
                success = True
                EVENTS_PROCESSED.labels(collector="consumer").inc()
                
            except Exception as e:
                # Database error - will be NACKed for retry
                logger.error(f"[❌ DB ERROR] Failed to store event {getattr(event, 'id', None)}: {type(e).__name__}: {str(e)}")
                if db:
                    try:
                        db.rollback()
                    except Exception as rb_err:
                        logger.error(f"[ERROR] Rollback failed: {rb_err}")
                success = False
                
            finally:
                if db:
                    try:
                        db.close()
                    except Exception:
                        pass
        
        # P1 Fix: ACK only on success, NACK on failure
        if success:
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            logger.warning(f"[⚠️  NACKED] Message returned to queue for retry")
    
    except json.JSONDecodeError as e:
        # Bad JSON - NACK without requeue (permanent failure)
        logger.error(f"[❌ JSON ERROR] Failed to parse JSON: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        
    except Exception as e:
        # Unexpected error - NACK with requeue
        logger.error(f"[❌ UNEXPECTED ERROR] {type(e).__name__}: {str(e)}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


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