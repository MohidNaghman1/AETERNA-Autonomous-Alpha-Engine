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
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
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
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
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
    _memory_cache = {h: exp for h, exp in _memory_cache.items() if exp > now}


def hash_content(content: str) -> str:
    """Generate SHA256 hash for event content.

    Args:
        content: Event content string to hash

    Returns:
        str: SHA256 hex digest of the content
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def is_duplicate(content: str) -> bool:
    """Check if content/ID exists (duplicate in 24-hour window).

    Tries Redis first, falls back to in-memory cache if unavailable.

    Supports both:
    - Full content hashing for semantic deduplication
    - Direct ID checking for faster lookups

    Args:
        content: Event content to check OR event ID for direct lookup

    Returns:
        bool: True if seen in the past 24 hours, False otherwise
    """
    # If content is short (looks like an ID), use it directly
    # Otherwise hash it for content comparison
    if len(content) < 50 and not any(c in content for c in [" ", "\n", "\t"]):
        # Likely an ID, use directly with prefix
        cache_key = f"event:{content}"
    else:
        # Content, hash it
        cache_key = f"content:{hash_content(content)}"

    if _redis_available and _redis:
        try:
            exists = _redis.exists(cache_key) == 1
            if exists:
                logger.debug(f"[DEDUP] Found in Redis: {cache_key[:50]}")
            return exists
        except Exception as e:
            logger.warning(f"Redis check failed, using memory cache: {e}")

    # Fallback to in-memory cache
    _cleanup_memory_cache()
    return cache_key in _memory_cache


def mark_as_seen(content: str, ttl_seconds: int = 86400) -> None:
    """Store content/ID with configurable TTL (default 24 hours).

    Tries Redis first, falls back to in-memory cache if unavailable.

    Args:
        content: Event content to mark as seen OR event ID
        ttl_seconds: Time-to-live in seconds (default 86400 = 24 hours)
    """
    # If content is short (looks like an ID), use it directly
    if len(content) < 50 and not any(c in content for c in [" ", "\n", "\t"]):
        cache_key = f"event:{content}"
    else:
        cache_key = f"content:{hash_content(content)}"

    if _redis_available and _redis:
        try:
            _redis.setex(cache_key, ttl_seconds, "1")
            logger.debug(
                f"[DEDUP] Marked in Redis: {cache_key[:50]} (TTL: {ttl_seconds}s)"
            )
            return
        except Exception as e:
            logger.warning(f"Redis mark failed, using memory cache: {e}")

    # Fallback to in-memory cache
    expiry = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    _memory_cache[cache_key] = expiry
