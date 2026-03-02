"""Content deduplication utility using Redis.

Uses SHA256 hashing and Redis with TTL to detect duplicate event content
within a rolling 1-hour window. Prevents duplicate alerts from being sent.
"""

import hashlib
import redis
import os
from datetime import timedelta

# Placeholder: Load from .env or settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
DEDUP_TTL_SECONDS = 3600  # 1 hour

# Redis connection (singleton)
_redis = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
)


def hash_content(content: str) -> str:
    """Generate SHA256 hash for event content.

    Args:
        content: Event content string to hash

    Returns:
        str: SHA256 hex digest of the content
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def is_duplicate(content: str) -> bool:
    """Check if content hash exists in Redis (duplicate in 1-hour window).

    Args:
        content: Event content to check

    Returns:
        bool: True if content was seen in the past hour, False otherwise
    """
    h = hash_content(content)
    return _redis.exists(h) == 1


def mark_as_seen(content: str) -> None:
    """Store content hash in Redis with 1-hour TTL.

    Args:
        content: Event content to mark as seen
    """
    h = hash_content(content)
    _redis.set(h, 1, ex=DEDUP_TTL_SECONDS)
