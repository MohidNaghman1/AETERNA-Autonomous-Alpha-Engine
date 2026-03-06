"""
RSS News Collector for crypto news sources.
- Polls CoinDesk, CoinTelegraph, Decrypt every 60 seconds
- Normalizes news to unified Event schema
- Publishes to RabbitMQ
- Deduplication and retry logic included
"""

import time
import feedparser
import pika
import os
import requests
import traceback
import logging
from dotenv import load_dotenv
from datetime import datetime
from app.modules.ingestion.domain.models import Event
from app.shared.utils.deduplication import is_duplicate, mark_as_seen
from app.shared.utils.entity_extraction import extract_crypto_mentions
from app.shared.utils.rabbitmq_publisher import RabbitMQPublisher
from app.shared.utils.monitoring import (
    EVENTS_PROCESSED,
    EVENT_PROCESSING_TIME,
    start_metrics_server,
)

# RSS Feeds
FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
]


# Load .env file
load_dotenv()


# RabbitMQ config (safe version)
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "events")

# RabbitMQ publisher utility
publisher = RabbitMQPublisher(queue_name=RABBITMQ_QUEUE)


# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("rss-collector")

RETRY_ATTEMPTS = 3
POLL_INTERVAL = 60  # seconds

# Start Prometheus metrics server (only once per process)
try:
    start_metrics_server(8001)
except Exception:
    pass


def normalize_entry(entry, source):
    content = {
        "title": entry.get("title"),
        "summary": entry.get("summary"),
        "link": entry.get("link"),
        "published": entry.get("published"),
        "source": source,
    }
    ts = datetime.utcnow()
    # Entity extraction from title and summary
    text = (entry.get("title") or "") + " " + (entry.get("summary") or "")
    entities = extract_crypto_mentions(text)
    return Event.create(
        source=source,
        type_="news",
        timestamp=ts,
        content=content,
        entities=entities,
        raw=entry,
    )


def validate_event(event: Event) -> bool:
    if not event.id or not event.timestamp or not event.content:
        return False
    if len(str(event.content)) < 10:
        return False
    return True


def publish_event(event: Event, _=None) -> bool:
    """Publish event to RabbitMQ. Returns True if successful, False otherwise."""
    if not validate_event(event):
        logger.warning(f"[INVALID] Event {event.id} failed validation, not published.")
        return False
    success = publisher.publish(event.model_dump_json())
    if not success:
        logger.error(f"[ERROR] Failed to publish event {event.id} after retries.")
    return success


def run_collector():
    """Single collection run - fetches all feeds once and returns.
    
    This is suitable for being called by Celery Beat which handles scheduling.
    Do NOT use this as an infinite loop - let Celery Beat manage the schedule.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    results = {"success": [], "failed": []}
    
    for feed_url in FEEDS:
        source = feed_url.split("//")[-1].split("/")[0]
        logger.info(f"Fetching feed: {feed_url} (source: {source})")
        
        for attempt in range(RETRY_ATTEMPTS):
            try:
                response = requests.get(feed_url, headers=headers, timeout=10)
                logger.info(f"HTTP status for {feed_url}: {response.status_code}")
                response.raise_for_status()
                feed = feedparser.parse(response.content)
                logger.info(
                    f"Feed '{source}' returned {len(feed.entries)} entries."
                )
                
                if not feed.entries:
                    logger.warning(f"No entries found in feed: {feed_url}")
                    results["failed"].append({"source": source, "reason": "No entries"})
                    continue
                
                entries_added = 0
                for entry in feed.entries:
                    event = normalize_entry(entry, source)
                    
                    if is_duplicate(event.id):
                        logger.info(f"Duplicate event skipped: {event.id}")
                        continue
                    
                    logger.info(
                        f"Publishing event: {event.id} | Source: {source} | Title: {event.content.get('title', 'N/A')[:50]}"
                    )
                    
                    with EVENT_PROCESSING_TIME.labels(collector="rss").time():
                        success = publish_event(event, None)
                        if success:
                            entries_added += 1
                    
                    EVENTS_PROCESSED.labels(collector="rss").inc()
                    mark_as_seen(event.id)
                
                results["success"].append({
                    "source": source, 
                    "total_entries": len(feed.entries),
                    "new_entries": entries_added
                })
                break  # Success, exit retry loop
                
            except Exception as e:
                logger.error(f"[ATTEMPT {attempt+1}] Failed to process {feed_url}: {type(e).__name__}: {str(e)}")
                logger.error(traceback.format_exc())
                
                if attempt == RETRY_ATTEMPTS - 1:
                    results["failed"].append({
                        "source": source, 
                        "reason": f"{type(e).__name__}: {str(e)[:100]}"
                    })
                elif attempt < RETRY_ATTEMPTS - 1:
                    logger.info(f"Retrying {feed_url} in {2 ** attempt} seconds...")
                    time.sleep(2**attempt)
    
    logger.info(f"RSS collection cycle completed. Success: {len(results['success'])}, Failed: {len(results['failed'])}")
    logger.info(f"Details: {results}")
    return results


def run_collector_loop():
    """Infinite loop version for standalone execution.
    
    Use this if running the collector as a standalone script, not via Celery.
    For Celery, use run_collector() and let Celery Beat handle scheduling.
    """
    while True:
        try:
            run_collector()
        except Exception as e:
            logger.error(f"[ERROR] Collection cycle failed: {str(e)}")
            logger.error(traceback.format_exc())
        
        logger.info(f"Sleeping for {POLL_INTERVAL} seconds before next poll.")
        time.sleep(POLL_INTERVAL)


# Alias for test compatibility
collect_and_publish = run_collector


if __name__ == "__main__":
    # Use the loop version when running standalone
    run_collector_loop()
