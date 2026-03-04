"""Content deduplication utility using Redis with fallback.

Uses SHA256 hashing and Redis with TTL to detect duplicate event content
within a rolling 1-hour window. Falls back to in-memory cache if Redis unavailable.
Prevents duplicate alerts from being sent.
"""

import hashlib
import redis
import os
import logging
from datetime import datetime, timedelta
from typing import Set, Tuple

logger = logging.getLogger(__name__)

# Placeholder: Load from .env or settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_URL = os.getenv("REDIS_URL")
DEDUP_TTL_SECONDS = 3600  # 1 hour

# Redis connection (singleton, optional)
_redis = None
_redis_available = False
# Fallback in-memory cache: (hash, expiry_time)
_memory_cache: dict = {}


def _init_redis():
    """Initialize Redis connection with error handling."""
    global _redis, _redis_available
    try:
        if REDIS_URL:
            _redis = redis.from_url(REDIS_URL, decode_responses=True)
        else:
            _redis = redis.StrictRedis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
        # Test connection
        _redis.ping()
        _redis_available = True
        logger.info("✅ Redis deduplication cache connected")
    except Exception as e:
        _redis_available = False
        logger.warning(
            f"⚠️  Redis unavailable, using in-memory cache for deduplication: {e}"
        )


# Initialize on import
_init_redis()


def _cleanup_memory_cache():
    """Remove expired entries from in-memory cache."""
    global _memory_cache
    now = datetime.utcnow()
    _memory_cache = {
        h: exp for h, exp in _memory_cache.items() if exp > now
    }


def hash_content(content: str) -> str:
    """Generate SHA256 hash for event content.

    Args:
        content: Event content string to hash

    Returns:
        str: SHA256 hex digest of the content
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def is_duplicate(content: str) -> bool:
    """Check if content hash exists (duplicate in 1-hour window).

    Tries Redis first, falls back to in-memory cache if unavailable.

    Args:
        content: Event content to check

    Returns:
        bool: True if content was seen in the past hour, False otherwise
    """
    h = hash_content(content)
    
    if _redis_available and _redis:
        try:
            return _redis.exists(h) == 1
        except Exception as e:
            logger.warning(f"Redis check failed, using memory cache: {e}")
    
    # Fallback to in-memory cache
    _cleanup_memory_cache()
    return h in _memory_cache


def mark_as_seen(content: str) -> None:
    """Store content hash with 1-hour TTL.

    Tries Redis first, falls back to in-memory cache if unavailable.

    Args:
        content: Event content to mark as seen
    """
    h = hash_content(content)
    
    if _redis_available and _redis:
        try:
            _redis.setex(h, DEDUP_TTL_SECONDS, "1")
            return
        except Exception as e:
            logger.warning(f"Redis mark failed, using memory cache: {e}")
    
    # Fallback to in-memory cache
    expiry = datetime.utcnow() + timedelta(seconds=DEDUP_TTL_SECONDS)
    _memory_cache[h] = expiry
    _redis.set(h, 1, ex=DEDUP_TTL_SECONDS)
