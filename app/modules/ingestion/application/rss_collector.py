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
from dotenv import load_dotenv
from datetime import datetime
from app.modules.ingestion.domain.models import Event
from app.shared.utils.deduplication import is_duplicate, mark_as_seen

# RSS Feeds
FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed"
]


# Load .env file
load_dotenv()

# RabbitMQ config (safe version)
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "events")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)

# Debug print for credentials
print("USER:", RABBITMQ_USER)
print("PASS:", RABBITMQ_PASSWORD)

RETRY_ATTEMPTS = 3
POLL_INTERVAL = 60  # seconds


def get_rabbitmq_connection():
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=5672,
        credentials=credentials
    )
    return pika.BlockingConnection(parameters)

def normalize_entry(entry, source):
    content = {
        "title": entry.get("title"),
        "summary": entry.get("summary"),
        "link": entry.get("link"),
        "published": entry.get("published"),
        "source": source
    }
    ts = datetime.utcnow()
    return Event.create(
        source=source,
        type_="news",
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
    headers = {"User-Agent": "Mozilla/5.0"}
    while True:
        for feed_url in FEEDS:
            source = feed_url.split("//")[-1].split("/")[0]
            for attempt in range(RETRY_ATTEMPTS):
                try:
                    response = requests.get(feed_url, headers=headers, timeout=10)
                    response.raise_for_status()
                    feed = feedparser.parse(response.content)
                    if not feed.entries:
                        continue
                    with get_rabbitmq_connection() as conn:
                        channel = conn.channel()
                        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
                        for entry in feed.entries:
                            event = normalize_entry(entry, source)
                            if is_duplicate(event.id):
                                continue
                            publish_event(event, channel)
                            mark_as_seen(event.id)
                    break  # Success, exit retry loop
                except Exception as e:
                    print(f"[ERROR] Failed to process {feed_url}: {str(e)}")
                    traceback.print_exc()
                    if attempt != RETRY_ATTEMPTS - 1:
                        time.sleep(2 ** attempt)
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run_collector()
