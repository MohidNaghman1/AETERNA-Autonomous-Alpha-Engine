"""
Agent A - The Sieve (Noise Filter)
Scoring logic for event filtering and prioritization.
"""

from typing import Dict, Any, List, Optional
import re
import numpy as np
from functools import lru_cache


# --- Multi-source check ---
def multi_source_check(event: Dict[str, Any], min_sources: int = 3) -> int:
    sources = event.get("sources", [])
    return (
        100
        if len(set(sources)) >= min_sources
        else int(100 * len(set(sources)) / min_sources)
    )


# --- Engagement analysis ---
def engagement_analysis(event: Dict[str, Any]) -> int:
    engagement_rate = event.get("engagement_rate", 0)
    verified = event.get("verified", False)
    score = (
        100 if engagement_rate > 0.05 else int(engagement_rate * 2000)
    )  # 0.05*2000=100
    if verified:
        score += 20
    return min(score, 120)


# --- Bot detection ---
def bot_detection(event: Dict[str, Any]) -> int:
    username = event.get("username", "")
    text = event.get("text", "")
    spam_patterns = [
        r"http[s]?://",
        r"free",
        r"giveaway",
        r"win",
        r"\d{5,}",
        r"buy now",
    ]
    generic_usernames = [r"user\d+", r"crypto\d+"]
    score = 100
    # Penalize for spam patterns
    for pat in spam_patterns:
        if re.search(pat, text, re.IGNORECASE):
            score -= 20
    # Penalize for generic usernames
    for pat in generic_usernames:
        if re.match(pat, username, re.IGNORECASE):
            score -= 20
    return max(score, 0)


# --- Semantic similarity detection ---


def semantic_similarity(
    event_embedding: List[float],
    db_embeddings: List[List[float]],
    threshold: float = 0.9,
) -> int:
    """
    Optimized: Uses numpy for batch cosine similarity.
    """
    if not db_embeddings or not event_embedding:
        return 100  # No similar events, so unique
    v1 = np.array(event_embedding)
    db = np.array(db_embeddings)
    if v1.ndim == 1:
        v1 = v1.reshape(1, -1)
    if db.ndim == 1:
        db = db.reshape(1, -1)
    # Normalize
    v1_norm = v1 / (np.linalg.norm(v1, axis=1, keepdims=True) + 1e-8)
    db_norm = db / (np.linalg.norm(db, axis=1, keepdims=True) + 1e-8)
    sims = np.dot(db_norm, v1_norm.T).flatten()
    max_sim = float(np.max(sims))
    return 100 if max_sim < threshold else int(100 * (1 - max_sim))


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
        return 0.0
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


# --- Optional: In-memory cache for recent embeddings (LRU, size 1000) ---
@lru_cache(maxsize=1000)
def get_cached_embeddings(key: str) -> Optional[List[List[float]]]:
    # Placeholder: Replace with actual DB/cache fetch if needed
    return None


# --- Weighted score calculation ---


def score_event(
    event: Dict[str, Any], db_embeddings: List[List[float]]
) -> Dict[str, Any]:
    ms_score = multi_source_check(event)
    eng_score = engagement_analysis(event)
    bot_score = bot_detection(event)
    dedup_score = semantic_similarity(event.get("embedding", []), db_embeddings)
    weighted = 0.3 * ms_score + 0.2 * eng_score + 0.3 * bot_score + 0.2 * dedup_score
    priority = "HIGH" if weighted >= 80 else ("MEDIUM" if weighted >= 50 else "LOW")
    return {
        "multi_source": ms_score,
        "engagement": eng_score,
        "bot": bot_score,
        "dedup": dedup_score,
        "score": weighted,
        "priority": priority,
    }


# --- Batch scoring for performance ---
def score_events_batch(
    events: List[Dict[str, Any]], db_embeddings: List[List[float]]
) -> List[Dict[str, Any]]:
    """
    Efficiently score a batch of events. Semantic similarity is vectorized.
    """
    results = []
    db = np.array(db_embeddings) if db_embeddings else None
    for event in events:
        ms_score = multi_source_check(event)
        eng_score = engagement_analysis(event)
        bot_score = bot_detection(event)
        # Vectorized deduplication if possible
        dedup_score = 100
        if db is not None and event.get("embedding"):
            v1 = np.array(event["embedding"])
            if v1.ndim == 1:
                v1 = v1.reshape(1, -1)
            db_norm = db / (np.linalg.norm(db, axis=1, keepdims=True) + 1e-8)
            v1_norm = v1 / (np.linalg.norm(v1, axis=1, keepdims=True) + 1e-8)
            sims = np.dot(db_norm, v1_norm.T).flatten()
            max_sim = float(np.max(sims))
            dedup_score = 100 if max_sim < 0.9 else int(100 * (1 - max_sim))
        weighted = (
            0.3 * ms_score + 0.2 * eng_score + 0.3 * bot_score + 0.2 * dedup_score
        )
        priority = "HIGH" if weighted >= 80 else ("MEDIUM" if weighted >= 50 else "LOW")
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
    return results
