"""
Twitter/X social collector for crypto-related posts.

- Polls the Twitter recent search API on a fixed interval
- Normalizes tweets to the shared Event schema
- Publishes to RabbitMQ
- Applies deduplication and lightweight engagement filtering
"""

import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List

import requests

from app.modules.ingestion.domain.models import Event
from app.shared.utils.data_extractors import extract_twitter_tweet_detailed
from app.shared.utils.deduplication import is_duplicate, mark_as_seen
from app.shared.utils.entity_extraction import extract_crypto_mentions
from app.shared.utils.monitoring import start_metrics_server
from app.shared.utils.rabbitmq_publisher import RabbitMQPublisher
from app.shared.utils.validators import validate_event as validate_event_schema

TWITTER_SEARCH_API = "https://api.twitter.com/2/tweets/search/recent"
POLL_INTERVAL = int(os.getenv("TWITTER_POLL_INTERVAL", "90"))
RETRY_ATTEMPTS = 3
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "events")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
TWITTER_SEARCH_QUERY = os.getenv(
    "TWITTER_SEARCH_QUERY",
    "(bitcoin OR btc OR ethereum OR eth OR solana OR sol OR crypto OR #bitcoin OR #ethereum) "
    "-is:retweet -is:reply lang:en",
)
TWITTER_MAX_RESULTS = max(10, min(int(os.getenv("TWITTER_MAX_RESULTS", "25")), 100))
TWITTER_MIN_ENGAGEMENTS = max(int(os.getenv("TWITTER_MIN_ENGAGEMENTS", "0")), 0)

publisher = RabbitMQPublisher(queue_name=RABBITMQ_QUEUE)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("twitter-collector")

try:
    start_metrics_server(8001)
except Exception:
    pass


def _build_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {TWITTER_BEARER_TOKEN}",
        "User-Agent": "AETERNA-TwitterCollector/1.0",
    }


def fetch_recent_tweets() -> List[Dict[str, Any]]:
    """Fetch recent tweets matching the configured crypto query."""
    if not TWITTER_BEARER_TOKEN:
        logger.warning(
            "TWITTER_BEARER_TOKEN is not set; skipping Twitter collection cycle."
        )
        return []

    params = {
        "query": TWITTER_SEARCH_QUERY,
        "max_results": TWITTER_MAX_RESULTS,
        "tweet.fields": (
            "created_at,lang,public_metrics,entities,possibly_sensitive,"
            "conversation_id,author_id"
        ),
        "expansions": "author_id",
        "user.fields": "name,username,verified,public_metrics",
    }

    backoff = 5
    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = requests.get(
                TWITTER_SEARCH_API,
                headers=_build_headers(),
                params=params,
                timeout=15,
            )
            if response.status_code == 429:
                logger.warning(
                    "Twitter API rate limited (attempt %s/%s). Sleeping %ss.",
                    attempt + 1,
                    RETRY_ATTEMPTS,
                    backoff,
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, 120)
                continue

            response.raise_for_status()
            payload = response.json()
            tweets = payload.get("data") or []
            includes = payload.get("includes") or {}
            users = {
                str(user.get("id")): user for user in includes.get("users", []) if user
            }

            hydrated = []
            for tweet in tweets:
                tweet_copy = dict(tweet)
                author_id = str(tweet_copy.get("author_id") or "")
                tweet_copy["_author"] = users.get(author_id, {})
                hydrated.append(tweet_copy)

            logger.info("Fetched %s tweets from Twitter recent search.", len(hydrated))
            return hydrated
        except requests.HTTPError as exc:
            logger.error("Twitter API HTTP error: %s", exc)
            if attempt == RETRY_ATTEMPTS - 1:
                raise
        except Exception as exc:
            logger.error("Twitter fetch failed: %s", exc)
            if attempt == RETRY_ATTEMPTS - 1:
                raise
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)

    return []


def normalize_tweet(tweet: Dict[str, Any]) -> Event:
    """Normalize a tweet into the unified Event schema."""
    author = tweet.get("_author") or {}
    content = extract_twitter_tweet_detailed(tweet, author=author)
    text = content.get("text", "")
    entities = extract_crypto_mentions(text)
    created_at = tweet.get("created_at")

    try:
        timestamp = (
            datetime.fromisoformat(created_at.replace("Z", "+00:00")).replace(tzinfo=None)
            if created_at
            else datetime.utcnow()
        )
    except ValueError:
        timestamp = datetime.utcnow()

    return Event.create(
        source="twitter",
        type_="social",
        timestamp=timestamp,
        content=content,
        entities=entities,
        raw={
            "tweet": {k: v for k, v in tweet.items() if k != "_author"},
            "author": author,
        },
    )


def validate_event(event: Event) -> bool:
    if not event.id or not event.timestamp or not event.content:
        return False
    if len(str(event.content)) < 10:
        return False

    is_valid, error_msg = validate_event_schema(event.model_dump())
    if not is_valid:
        logger.warning("[SCHEMA-VALIDATION-FAILED] %s", error_msg)
        return False
    return True


def publish_event(event: Event) -> bool:
    if not validate_event(event):
        logger.warning("[INVALID] Event %s failed validation, not published.", event.id)
        return False
    success = publisher.publish(event.model_dump_json())
    if not success:
        logger.error("[ERROR] Failed to publish Twitter event %s.", event.id)
    return success


def _engagement_total(content: Dict[str, Any]) -> int:
    engagement = content.get("engagement") or {}
    return sum(
        int(engagement.get(metric, 0) or 0)
        for metric in ("likes", "retweets", "replies", "quotes", "bookmarks")
    )


def run_collector():
    """Single Twitter collection cycle suitable for schedulers."""
    try:
        tweets = fetch_recent_tweets()
    except Exception as exc:
        logger.error("[ERROR] Failed to fetch tweets: %s", exc)
        return

    if not tweets:
        logger.info("No Twitter events fetched this cycle.")
        return

    published = 0
    skipped_duplicate = 0
    skipped_low_engagement = 0

    for tweet in tweets:
        try:
            event = normalize_tweet(tweet)
        except Exception as exc:
            logger.error("Failed to normalize tweet %s: %s", tweet.get("id"), exc)
            continue

        if _engagement_total(event.content) < TWITTER_MIN_ENGAGEMENTS:
            skipped_low_engagement += 1
            continue

        if is_duplicate(event.id):
            skipped_duplicate += 1
            logger.info("Duplicate Twitter event skipped: %s", event.id)
            continue

        if publish_event(event):
            mark_as_seen(event.id)
            published += 1

    logger.info(
        "Twitter collection cycle completed. Published=%s, duplicates=%s, low_engagement=%s",
        published,
        skipped_duplicate,
        skipped_low_engagement,
    )


def run_collector_loop():
    """Standalone loop mode for local debugging."""
    while True:
        try:
            run_collector()
        except Exception as exc:
            logger.error("[ERROR] Twitter collection cycle failed: %s", exc)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_collector_loop()
