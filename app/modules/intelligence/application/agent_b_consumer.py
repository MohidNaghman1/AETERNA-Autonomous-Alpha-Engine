"""
Agent B Consumer - The Profiler (Wallet Entity Identification)
===============================================================

Reads filtered events from Agent A
Enriches them with wallet profiling data
Publishes enriched events to downstream agents (Agent C, D)
"""

import json
import pika
import os
import logging

from app.modules.intelligence.application.agent_b import (
    profile_wallet_from_event,
    enrich_event_with_profiling,
    ProfilerConfig,
)
from app.config.db import SessionLocal

# Optional: load .env for local dev
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("agent-b-consumer")

# Configuration
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
QUEUE_NAME_IN = os.environ.get("RABBITMQ_AGENT_B_QUEUE_IN", "events_processed")
QUEUE_NAME_OUT = os.environ.get("RABBITMQ_AGENT_B_QUEUE_OUT", "events_profiled")
PREFETCH_COUNT = int(os.environ.get("RABBITMQ_PREFETCH_COUNT", 10))
RABBITMQ_DLQUEUE = os.environ.get("RABBITMQ_DL_QUEUE", "events_profiling_dlq")


def save_profiling_result(event: dict, profiling_output_dict: dict):
    """
    Save Agent B profiling result to database.

    Args:
        event: Original event
        profiling_output_dict: Profiling output as dict
    """
    db = SessionLocal()
    try:
        # This would save to a table like profiled_events if needed
        # For now, we primarily pass it downstream to Agent C
        logger.debug(
            f"Profiling result saved: {event.get('id', 'unknown')} -> "
            f"{profiling_output_dict.get('profiling_signal', 'unknown')}"
        )
    except Exception as e:
        logger.error(f"Error saving profiling result: {e}")
    finally:
        db.close()


def publish_enriched_event(
    channel: pika.adapters.blocking_connection.BlockingChannel,
    enriched_event: dict,
):
    """
    Publish enriched event to downstream queue (Agent C).

    Args:
        channel: RabbitMQ channel
        enriched_event: Event with agent_b enrichment data
    """
    try:
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME_OUT,
            body=json.dumps(enriched_event),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent
                content_type="application/json",
            ),
        )
        logger.debug(f"Published enriched event: {enriched_event.get('id', 'unknown')}")
    except Exception as e:
        logger.error(f"Error publishing enriched event: {e}")
        raise


def process_event(
    channel: pika.adapters.blocking_connection.BlockingChannel,
    event: dict,
    db,
    config: ProfilerConfig = None,
) -> bool:
    """
    Process a single event through Agent B.

    Args:
        channel: RabbitMQ channel
        event: Event dict from Agent A
        db: Database session
        config: Profiler configuration

    Returns:
        True if successful, False if failed
    """
    if config is None:
        config = ProfilerConfig()

    try:
        logger.info(f"[AGENT B] Processing event: {event.get('id', 'unknown')}")

        # Extract wallet address from event
        wallet_addr = event.get("wallet_address") or event.get("address")
        if not wallet_addr:
            logger.warning(f"Event {event.get('id', 'unknown')} missing wallet address")
            return True  # Skip but don't fail

        # Profile the wallet
        profiling_output = profile_wallet_from_event(
            wallet_address=wallet_addr,
            event_id=event.get("id", "unknown"),
            event_data=event,
            db=db,
            config=config,
        )

        # Convert to dict for storage/transmission
        profiling_dict = profiling_output.model_dump(mode="json")

        # Save result
        save_profiling_result(event, profiling_dict)

        # Enrich event
        enriched_event = enrich_event_with_profiling(event, profiling_output)

        # Publish downstream
        publish_enriched_event(channel, enriched_event)

        logger.info(
            f"[AGENT B] ✓ Processed event {event.get('id', 'unknown')}: "
            f"{profiling_output.profiling_signal} "
            f"(boost={profiling_output.should_boost_priority})"
        )
        return True

    except Exception as e:
        logger.error(
            f"[AGENT B] ✗ Error processing event {event.get('id', 'unknown')}: {e}",
            exc_info=True,
        )
        return False


def callback(
    ch: pika.adapters.blocking_connection.BlockingChannel,
    method: pika.spec.Basic.Deliver,
    properties: pika.spec.BasicProperties,
    body: bytes,
):
    """
    RabbitMQ message callback.

    Args:
        ch: Channel
        method: Delivery method
        properties: Message properties
        body: Message body
    """
    db = SessionLocal()
    try:
        # Parse message
        event = json.loads(body.decode("utf-8"))
        logger.debug(f"Received event: {event.get('id', 'unknown')}")

        # Process through Agent B
        config = ProfilerConfig()
        success = process_event(ch, event, db, config)

        # Acknowledge if successful
        if success:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.debug(f"Acknowledged event: {event.get('id', 'unknown')}")
        else:
            # Reject and send to DLQ (will retry or be dead-lettered)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            logger.warning(
                f"Rejected event {event.get('id', 'unknown')} - will be sent to DLQ"
            )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logger.error(f"Unhandled error in callback: {e}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    finally:
        db.close()


def start_consumer():
    """Start the Agent B consumer."""
    logger.info(f"[AGENT B CONSUMER] Starting...")
    logger.info(f"  RabbitMQ Host: {RABBITMQ_HOST}:{RABBITMQ_PORT}")
    logger.info(f"  Input Queue: {QUEUE_NAME_IN}")
    logger.info(f"  Output Queue: {QUEUE_NAME_OUT}")
    logger.info(f"  DLQ: {RABBITMQ_DLQUEUE}")

    try:
        # Connect to RabbitMQ
        credentials = pika.PlainCredentials(
            os.environ.get("RABBITMQ_USER", "guest"),
            os.environ.get("RABBITMQ_PASSWORD", "guest"),
        )
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
            )
        )
        channel = connection.channel()

        # Declare queues with DLX
        channel.queue_declare(queue=QUEUE_NAME_IN, durable=True)
        channel.queue_declare(queue=QUEUE_NAME_OUT, durable=True)
        channel.queue_declare(queue=RABBITMQ_DLQUEUE, durable=True)

        # Set prefetch count
        channel.basic_qos(prefetch_count=PREFETCH_COUNT)

        # Set up consumer
        channel.basic_consume(
            queue=QUEUE_NAME_IN, on_message_callback=callback, auto_ack=False
        )

        logger.info("[AGENT B CONSUMER] Waiting for messages...")
        channel.start_consuming()

    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        raise
    except KeyboardInterrupt:
        logger.info("[AGENT B CONSUMER] Shutting down...")
        if connection.is_open:
            connection.close()
    except Exception as e:
        logger.error(f"Fatal error in consumer: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    start_consumer()
