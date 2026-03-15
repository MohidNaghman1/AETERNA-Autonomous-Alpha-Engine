"""
Agent A - The Sieve (Noise Filter)
Scoring logic for event filtering and prioritization.

Enhanced with:
- Configuration management
- Input validation (Pydantic models)
- Comprehensive logging
- Improved error handling
- Type safety
"""

from typing import Dict, Any, List, Optional, Tuple
import re
import numpy as np
from functools import lru_cache
import logging
from pydantic import BaseModel, field_validator, ConfigDict
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)


# --- Configuration ---
@dataclass
class ScoringConfig:
    """Centralized scoring configuration."""

    min_sources: int = 3
    min_engagement_rate: float = 0.05
    engagement_multiplier: int = 2000
    engagement_bonus: int = 20
    dedup_threshold: float = 0.9
    high_priority_threshold: float = 80.0
    medium_priority_threshold: float = 50.0

    # Weights (must sum to 1.0)
    weight_multi_source: float = 0.3
    weight_engagement: float = 0.2
    weight_bot_detection: float = 0.3
    weight_deduplication: float = 0.2

    # Bot detection
    spam_patterns: List[str] = None
    generic_username_patterns: List[str] = None
    spam_penalty: int = 20
    username_penalty: int = 20

    # Cache size
    embedding_cache_size: int = 1000

    def __post_init__(self):
        if self.spam_patterns is None:
            self.spam_patterns = [
                r"http[s]?://",
                r"free",
                r"giveaway",
                r"win",
                r"\d{5,}",
                r"buy now",
            ]
        if self.generic_username_patterns is None:
            self.generic_username_patterns = [r"user\d+", r"crypto\d+"]

        # Validate weights sum to 1.0
        weight_sum = (
            self.weight_multi_source
            + self.weight_engagement
            + self.weight_bot_detection
            + self.weight_deduplication
        )
        if not np.isclose(weight_sum, 1.0):
            logger.warning(f"Weights sum to {weight_sum}, not 1.0. Normalizing...")
            total = weight_sum
            self.weight_multi_source /= total
            self.weight_engagement /= total
            self.weight_bot_detection /= total
            self.weight_deduplication /= total


# --- Pydantic Models for Validation ---
class EventModel(BaseModel):
    """Validated event structure."""

    model_config = ConfigDict(extra="allow")

    sources: Optional[List[str]] = None
    engagement_rate: Optional[float] = None
    verified: Optional[bool] = False
    username: Optional[str] = ""
    text: Optional[str] = ""
    embedding: Optional[List[float]] = None

    @field_validator("engagement_rate")
    @classmethod
    def validate_engagement_rate(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 1):
            raise ValueError("engagement_rate must be between 0 and 1")
        return v

    @field_validator("embedding")
    @classmethod
    def validate_embedding(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is not None and len(v) == 0:
            return None
        return v


class ScoringResult(BaseModel):
    """Standardized scoring result."""

    multi_source: float
    engagement: float
    bot: float
    dedup: float
    score: float
    priority: str
    details: Optional[Dict[str, Any]] = None


# --- Multi-source check ---
def multi_source_check(
    event: Dict[str, Any], config: Optional[ScoringConfig] = None
) -> int:
    """
    Score based on number of unique sources.

    Args:
        event: Event dictionary
        config: Scoring configuration

    Returns:
        Score 0-100
    """
    if config is None:
        config = ScoringConfig()

    try:
        sources = event.get("sources") or []
        if not isinstance(sources, list):
            logger.warning(f"Sources not a list: {type(sources)}. Converting to list.")
            sources = [sources] if sources else []

        unique_sources = len(set(sources))
        if unique_sources >= config.min_sources:
            return 100

        score = int(100 * unique_sources / config.min_sources)
        return min(score, 100)
    except Exception as e:
        logger.error(f"Error in multi_source_check: {e}", exc_info=True)
        return 50  # Return neutral score on error


# --- Engagement analysis ---
def engagement_analysis(
    event: Dict[str, Any], config: Optional[ScoringConfig] = None
) -> int:
    """
    Score based on engagement rate and verification status.

    Args:
        event: Event dictionary
        config: Scoring configuration

    Returns:
        Score 0-120 (bonus possible for verified)
    """
    if config is None:
        config = ScoringConfig()

    try:
        engagement_rate = event.get("engagement_rate", 0)
        if not isinstance(engagement_rate, (int, float)):
            logger.warning(f"engagement_rate not numeric: {type(engagement_rate)}")
            engagement_rate = 0

        # Clamp to valid range
        engagement_rate = max(0, min(engagement_rate, 1.0))

        score = (
            100
            if engagement_rate > config.min_engagement_rate
            else int(engagement_rate * config.engagement_multiplier)
        )

        verified = event.get("verified", False)
        if verified:
            score += config.engagement_bonus

        return min(score, 120)
    except Exception as e:
        logger.error(f"Error in engagement_analysis: {e}", exc_info=True)
        return 50  # Return neutral score on error


# --- Bot detection ---
def bot_detection(event: Dict[str, Any], config: Optional[ScoringConfig] = None) -> int:
    """
    Score based on bot detection heuristics.

    Args:
        event: Event dictionary
        config: Scoring configuration

    Returns:
        Score 0-100
    """
    if config is None:
        config = ScoringConfig()

    try:
        username = event.get("username", "")
        text = event.get("text", "")

        if not isinstance(username, str):
            logger.warning(f"Username not string: {type(username)}")
            username = str(username)
        if not isinstance(text, str):
            logger.warning(f"Text not string: {type(text)}")
            text = str(text)

        score = 100

        # Penalize for spam patterns
        for pattern in config.spam_patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    score -= config.spam_penalty
                    logger.debug(f"Spam pattern matched: {pattern}")
            except re.error as e:
                logger.error(f"Invalid regex pattern: {pattern}, error: {e}")

        # Penalize for generic usernames
        for pattern in config.generic_username_patterns:
            try:
                if re.match(pattern, username, re.IGNORECASE):
                    score -= config.username_penalty
                    logger.debug(f"Generic username matched: {pattern}")
            except re.error as e:
                logger.error(f"Invalid regex pattern: {pattern}, error: {e}")

        return max(score, 0)
    except Exception as e:
        logger.error(f"Error in bot_detection: {e}", exc_info=True)
        return 50  # Return neutral score on error


# --- Semantic similarity detection ---
def semantic_similarity(
    event_embedding: Optional[List[float]],
    db_embeddings: Optional[List[List[float]]],
    config: Optional[ScoringConfig] = None,
) -> int:
    """
    Compute semantic similarity using vectorized cosine similarity.

    Args:
        event_embedding: Embedding vector for event
        db_embeddings: Collection of embeddings to compare against
        config: Scoring configuration

    Returns:
        Score 0-100 (lower score = more similar)
    """
    if config is None:
        config = ScoringConfig()

    try:
        # Validate inputs
        if not event_embedding or not db_embeddings:
            logger.debug("No embeddings to compare, returning perfect uniqueness")
            return 100  # No similar events, so unique

        v1 = np.array(event_embedding, dtype=np.float32)
        db = np.array(db_embeddings, dtype=np.float32)

        # Handle 1D arrays
        if v1.ndim == 1:
            v1 = v1.reshape(1, -1)
        if db.ndim == 1:
            db = db.reshape(1, -1)

        # Normalize vectors
        v1_norm = np.linalg.norm(v1, axis=1, keepdims=True)
        db_norm = np.linalg.norm(db, axis=1, keepdims=True)

        # Check for zero vectors
        v1_norm = np.where(v1_norm == 0, 1e-8, v1_norm)
        db_norm = np.where(db_norm == 0, 1e-8, db_norm)

        v1_normalized = v1 / v1_norm
        db_normalized = db / db_norm

        # Batch cosine similarity
        similarities = np.dot(db_normalized, v1_normalized.T).flatten()
        max_similarity = float(np.max(similarities))

        # Handle NaN/inf
        if not np.isfinite(max_similarity):
            logger.warning(f"Non-finite similarity: {max_similarity}")
            return 100

        score = (
            100
            if max_similarity < config.dedup_threshold
            else int(100 * (1 - max_similarity))
        )
        return max(0, min(score, 100))
    except Exception as e:
        logger.error(f"Error in semantic_similarity: {e}", exc_info=True)
        return 100  # Return neutral (unique) score on error


def cosine_similarity(
    vec1: Optional[List[float]], vec2: Optional[List[float]]
) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Similarity score 0-1
    """
    try:
        if not vec1 or not vec2:
            return 0.0

        v1 = np.array(vec1, dtype=np.float32)
        v2 = np.array(vec2, dtype=np.float32)

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = float(np.dot(v1, v2) / (norm1 * norm2))

        # Handle NaN/inf
        if not np.isfinite(similarity):
            logger.warning(f"Non-finite cosine similarity: {similarity}")
            return 0.0

        return max(0.0, min(similarity, 1.0))
    except Exception as e:
        logger.error(f"Error in cosine_similarity: {e}", exc_info=True)
        return 0.0


# --- In-memory cache for recent embeddings ---
@lru_cache(maxsize=1000)
def get_cached_embeddings(key: str) -> Optional[List[List[float]]]:
    """
    Retrieve cached embeddings by key.

    Note: This is a placeholder. For production, integrate with Redis or similar.
    The cache is useful for reducing repeated embeddings lookups.

    Args:
        key: Cache key

    Returns:
        Cached embeddings or None
    """
    logger.debug(f"Cache miss for key: {key}")
    return None


# --- Weighted score calculation ---
def score_event(
    event: Dict[str, Any],
    db_embeddings: Optional[List[List[float]]] = None,
    config: Optional[ScoringConfig] = None,
    return_details: bool = False,
) -> Dict[str, Any]:
    """
    Score a single event using weighted metrics.

    Args:
        event: Event to score
        db_embeddings: Database embeddings for deduplication
        config: Scoring configuration
        return_details: Include detailed breakdown

    Returns:
        Dictionary with scores and priority
    """
    if config is None:
        config = ScoringConfig()

    try:
        # Validate event
        validated_event = EventModel(**event)
        event_dict = validated_event.model_dump()
    except Exception as e:
        logger.warning(f"Event validation failed: {e}. Using raw event.")
        event_dict = event

    try:
        # ========================================================================
        # THRESHOLD-BASED PRIORITY OPTIMIZATION
        # Check if event has priority_marker from on-chain collector
        # If so, honor it as a fast-track determination (no complex scoring needed)
        # ========================================================================
        priority_marker = event_dict.get("content", {}).get("priority_marker")
        priority_reason = event_dict.get("content", {}).get("priority_reason", "")
        
        if priority_marker in ("HIGH", "MEDIUM", "LOW"):
            # Use on-chain collector's threshold-based priority
            if priority_marker == "HIGH":
                score = 95.0
            elif priority_marker == "MEDIUM":
                score = 70.0
            else:  # LOW
                score = 35.0
            
            priority = priority_marker
            result = {
                "multi_source": 0,
                "engagement": 0,
                "bot": 0,
                "dedup": 0,
                "score": score,
                "priority": priority,
                "technique": "threshold_based",  # ← Mark as threshold-based
                "reason": priority_reason,
            }
            logger.info(
                f"[PRIORITY] Fast-tracked on-chain event: {priority} "
                f"(${event_dict.get('content', {}).get('usd_value', 'N/A')}). "
                f"Reason: {priority_reason}"
            )
            return result
        
        # ========================================================================
        # STANDARD AGENT A SCORING (for non-on-chain or borderline events)
        # ========================================================================
        ms_score = multi_source_check(event_dict, config)
        eng_score = engagement_analysis(event_dict, config)
        bot_score = bot_detection(event_dict, config)
        dedup_score = semantic_similarity(
            event_dict.get("embedding"), db_embeddings, config
        )

        # Weighted calculation
        weighted = (
            config.weight_multi_source * ms_score
            + config.weight_engagement * eng_score
            + config.weight_bot_detection * bot_score
            + config.weight_deduplication * dedup_score
        )

        # Assign priority
        if weighted >= config.high_priority_threshold:
            priority = "HIGH"
        elif weighted >= config.medium_priority_threshold:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        result = {
            "multi_source": ms_score,
            "engagement": eng_score,
            "bot": bot_score,
            "dedup": dedup_score,
            "score": weighted,
            "priority": priority,
            "technique": "agent_a_scoring",  # ← Mark as AI scoring
        }

        if return_details:
            result["details"] = {
                "weights": {
                    "multi_source": config.weight_multi_source,
                    "engagement": config.weight_engagement,
                    "bot_detection": config.weight_bot_detection,
                    "deduplication": config.weight_deduplication,
                },
                "event_fields": list(event_dict.keys()),
            }

        logger.debug(f"Scored event: priority={priority}, score={weighted:.2f}")
        return result
    except Exception as e:
        logger.error(f"Error scoring event: {e}", exc_info=True)
        return {
            "multi_source": 0,
            "engagement": 0,
            "bot": 0,
            "dedup": 0,
            "score": 0,
            "priority": "LOW",
            "error": str(e),
        }


# --- Batch scoring for performance ---
def score_events_batch(
    events: List[Dict[str, Any]],
    db_embeddings: Optional[List[List[float]]] = None,
    config: Optional[ScoringConfig] = None,
) -> List[Dict[str, Any]]:
    """
    Efficiently score a batch of events with vectorized operations.

    Args:
        events: List of events to score
        db_embeddings: Database embeddings for deduplication
        config: Scoring configuration

    Returns:
        List of scoring results
    """
    if config is None:
        config = ScoringConfig()

    if not events:
        logger.warning("No events to score")
        return []

    results = []
    db = None
    db_norm = None

    # Pre-compute normalized DB embeddings once
    if db_embeddings:
        try:
            db = np.array(db_embeddings, dtype=np.float32)
            if db.ndim == 1:
                db = db.reshape(1, -1)
            db_norms = np.linalg.norm(db, axis=1, keepdims=True)
            db_norms = np.where(db_norms == 0, 1e-8, db_norms)
            db_norm = db / db_norms
        except Exception as e:
            logger.error(f"Error pre-computing DB embeddings: {e}")
            db = None
            db_norm = None

    logger.info(f"Scoring batch of {len(events)} events")

    for idx, event in enumerate(events):
        try:
            # Validate event
            try:
                validated_event = EventModel(**event)
                event_dict = validated_event.model_dump()
            except Exception as e:
                logger.warning(f"Event {idx} validation failed: {e}")
                event_dict = event

            # Score components
            ms_score = multi_source_check(event_dict, config)
            eng_score = engagement_analysis(event_dict, config)
            bot_score = bot_detection(event_dict, config)

            # Optimized deduplication score
            dedup_score = 100
            if db_norm is not None and event_dict.get("embedding"):
                try:
                    v1 = np.array(event_dict["embedding"], dtype=np.float32)
                    if v1.ndim == 1:
                        v1 = v1.reshape(1, -1)
                    v1_norms = np.linalg.norm(v1, axis=1, keepdims=True)
                    v1_norms = np.where(v1_norms == 0, 1e-8, v1_norms)
                    v1_norm = v1 / v1_norms
                    similarities = np.dot(db_norm, v1_norm.T).flatten()
                    max_sim = float(np.max(similarities))
                    if np.isfinite(max_sim):
                        dedup_score = (
                            100
                            if max_sim < config.dedup_threshold
                            else int(100 * (1 - max_sim))
                        )
                except Exception as e:
                    logger.error(f"Event {idx} dedup score error: {e}")
                    dedup_score = 100

            # Weighted calculation
            weighted = (
                config.weight_multi_source * ms_score
                + config.weight_engagement * eng_score
                + config.weight_bot_detection * bot_score
                + config.weight_deduplication * dedup_score
            )

            # Assign priority
            if weighted >= config.high_priority_threshold:
                priority = "HIGH"
            elif weighted >= config.medium_priority_threshold:
                priority = "MEDIUM"
            else:
                priority = "LOW"

            results.append(
                {
                    "multi_source": ms_score,
                    "engagement": eng_score,
                    "bot": bot_score,
                    "dedup": dedup_score,
                    "score": weighted,
                    "priority": priority,
                }
            )
        except Exception as e:
            logger.error(f"Error scoring event {idx}: {e}", exc_info=True)
            results.append(
                {
                    "multi_source": 0,
                    "engagement": 0,
                    "bot": 0,
                    "dedup": 0,
                    "score": 0,
                    "priority": "LOW",
                    "error": str(e),
                }
            )

    logger.info(f"Batch scoring complete: {len(results)} results")
    return results
