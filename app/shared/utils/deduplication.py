"""
Deduplication utility for event content using Redis.
- Hashes event content
- Checks/marks duplicates in Redis (1-hour window)
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
    """Generate SHA256 hash for event content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def is_duplicate(content: str) -> bool:
    """Check if content hash exists in Redis (duplicate in 1-hour window)."""
    h = hash_content(content)
    return _redis.exists(h) == 1


def mark_as_seen(content: str):
    """Store content hash in Redis with 1-hour TTL."""
    h = hash_content(content)
    _redis.set(h, 1, ex=DEDUP_TTL_SECONDS)

