"""
Price Data Collector for CoinGecko API.
- Polls top 100 cryptocurrencies every 60 seconds
- Calculates price changes (1h, 24h), detects significant moves (>5%)
- Normalizes to unified Event schema
- Publishes to RabbitMQ
- Deduplication and retry logic included
"""

import time
import requests
import os
import logging
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
from app.shared.utils.data_extractors import (
    extract_price_entry_detailed,
    identify_significant_changes,
)
from app.shared.utils.validators import validate_event as validate_event_schema

COINGECKO_API = "https://api.coingecko.com/api/v3/coins/markets"
POLL_INTERVAL = 60  # seconds
RETRY_ATTEMPTS = 3

RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "events")

# RabbitMQ publisher utility
publisher = RabbitMQPublisher(queue_name=RABBITMQ_QUEUE)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("price-collector")

# Start Prometheus metrics server (only once per process)
try:
    start_metrics_server(8001)
except Exception:
    pass


def fetch_prices():
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 250,  # Increased from 100 to track top 250 coins by market cap
        "page": 1,
        "price_change_percentage": "1h,24h,7d,14d,30d,1y",  # Extended timeframes
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_market_cap_change_percentage": "true",
        "include_last_updated_at": "true",
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    backoff = 10
    while True:
        try:
            logger.info(f"Fetching prices from CoinGecko: {COINGECKO_API}")
            resp = requests.get(
                COINGECKO_API, params=params, headers=headers, timeout=10
            )
            logger.info(f"HTTP status for CoinGecko: {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"CoinGecko returned {len(data)} price entries.")
            return data
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                logger.warning(f"Rate limited. Sleeping {backoff}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)  # Exponential backoff up to 5 min
            else:
                logger.error(f"HTTP error fetching prices: {e}")
                raise e
        except Exception as e:
            logger.error(f"Error fetching prices: {e}. Retrying in {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)


def normalize_price_entry(entry):
    """
    Normalize and enrich CoinGecko price entry to Event format.
    Extracts detailed price metrics, risk scores, and significant changes.
    """
    # Extract detailed price content
    content = extract_price_entry_detailed(entry)

    # Identify significant changes
    significance_info = identify_significant_changes(
        content, significance_threshold_pct=5.0
    )
    content.update(significance_info)

    ts = datetime.utcnow()

    # Entity extraction from symbol and name
    text = (entry.get("symbol") or "") + " " + (entry.get("name") or "")
    entities = extract_crypto_mentions(text)

    return Event.create(
        source="coingecko",
        type_="price",
        timestamp=ts,
        content=content,
        entities=entities,
        raw=entry,
    )


def validate_event(event: Event) -> bool:
    """Validate event using schema validation"""
    if not event.id or not event.timestamp or not event.content:
        return False
    if len(str(event.content)) < 10:
        return False

    # Schema validation
    is_valid, error_msg = validate_event_schema(event.model_dump())
    if not is_valid:
        logger.warning(f"[SCHEMA-VALIDATION-FAILED] {error_msg}")
        return False

    return True


def publish_event(event: Event, _metadata=None):
    if not validate_event(event):
        logger.warning(f"[INVALID] Event {event.id} failed validation, not published.")
        return
    success = publisher.publish(event.model_dump_json())
    if not success:
        logger.error(f"[ERROR] Failed to publish event {event.id} after retries.")


def run_collector():
    """Single collection run - fetches prices once and returns.

    This is suitable for being called by Celery Beat which handles scheduling.
    Do NOT use this as an infinite loop - let Celery Beat manage the schedule.
    """
    for attempt in range(RETRY_ATTEMPTS):
        try:
            prices = fetch_prices()
            published = 0
            skipped_no_significance = 0
            skipped_duplicate = 0

            for entry in prices:
                event = normalize_price_entry(entry)

                # Check for significance (5% or more change in 1h)
                significance_info = event.content.get("significant_moves", [])
                if not significance_info:
                    skipped_no_significance += 1
                    continue

                if is_duplicate(event.id):
                    logger.info(f"Duplicate price event skipped: {event.id}")
                    skipped_duplicate += 1
                    continue

                alert_reasons = event.content.get(
                    "alert_reasons", "Price movement detected"
                )
                logger.info(
                    f"Publishing price event: {event.id} | Symbol: {event.content.get('symbol')} | {alert_reasons}"
                )
                publish_event(event, None)
                mark_as_seen(event.id)
                published += 1

            logger.info(
                f"Published {published} price events this cycle. "
                f"Skipped: {skipped_no_significance} (no significance), "
                f"{skipped_duplicate} (duplicate)."
            )
            break

        except Exception as e:
            if attempt == RETRY_ATTEMPTS - 1:
                logger.error(f"[ERROR] Failed to fetch/publish prices: {e}")
            else:
                logger.info(f"Retrying CoinGecko fetch in {2 ** attempt} seconds...")
                time.sleep(2**attempt)

    logger.info("Price collection cycle completed.")


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

        logger.info(f"Sleeping for {POLL_INTERVAL} seconds before next price poll.")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    # Use the loop version when running standalone
    run_collector_loop()
