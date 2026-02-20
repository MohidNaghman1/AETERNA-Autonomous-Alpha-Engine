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
import pika
import os
from datetime import datetime
from app.modules.ingestion.domain.models import Event
from app.shared.utils.deduplication import is_duplicate, mark_as_seen

COINGECKO_API = "https://api.coingecko.com/api/v3/coins/markets"
POLL_INTERVAL = 60  # seconds
RETRY_ATTEMPTS = 3


RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "events")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")


def get_rabbitmq_connection():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=5672,
            credentials=credentials
        )
    )

def fetch_prices():
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "price_change_percentage": "1h,24h"
    }
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    backoff = 10
    while True:
        try:
            resp = requests.get(COINGECKO_API, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                print(f"Rate limited. Sleeping {backoff}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)  # Exponential backoff up to 5 min
            else:
                raise e
        except Exception as e:
            print(f"Error fetching prices: {e}. Retrying in {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)

def normalize_price_entry(entry):
    content = {
        "id": entry["id"],
        "symbol": entry["symbol"],
        "name": entry["name"],
        "current_price": entry["current_price"],
        "price_change_percentage_1h": entry.get("price_change_percentage_1h_in_currency"),
        "price_change_percentage_24h": entry.get("price_change_percentage_24h_in_currency"),
        "market_cap": entry["market_cap"],
        "last_updated": entry["last_updated"]
    }
    ts = datetime.utcnow()
    return Event.create(
        source="coingecko",
        type_="price",
        timestamp=ts,
        content=content,
        raw=entry
    )

def publish_event(event, channel):
    channel.basic_publish(
        exchange='',
        routing_key=RABBITMQ_QUEUE,
        body=event.model_dump_json()
    )

def run_collector():
    while True:
        for attempt in range(RETRY_ATTEMPTS):
            try:
                prices = fetch_prices()
                with get_rabbitmq_connection() as conn:
                    channel = conn.channel()
                    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
                    for entry in prices:
                        # Detect significant move
                        p1h = entry.get("price_change_percentage_1h_in_currency")
                        if p1h is not None and abs(p1h) < 5:
                            continue
                        event = normalize_price_entry(entry)
                        if is_duplicate(event.id):
                            continue
                        publish_event(event, channel)
                        mark_as_seen(event.id)
                break
            except Exception as e:
                if attempt == RETRY_ATTEMPTS - 1:
                    print(f"[ERROR] Failed to fetch/publish prices: {e}")
                else:
                    time.sleep(2 ** attempt)
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run_collector()
