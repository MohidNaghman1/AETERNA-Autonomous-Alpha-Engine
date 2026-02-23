"""
Unified Event model for normalized ingestion events.
- Used for news, price, and other event types
- Ensures consistent schema across collectors
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import hashlib


class Event(BaseModel):
    id: str = Field(..., description="Unique event ID (hash)")
    source: str = Field(..., description="Source system or feed (e.g., 'coindesk', 'coingecko')")
    type: str = Field(..., description="Event type (e.g., 'news', 'price')")
    timestamp: str = Field(..., description="UTC ISO8601 timestamp")
    content: Dict[str, Any] = Field(..., description="Normalized event payload")
    entities: Optional[list[str]] = Field(default_factory=list, description="Extracted crypto mentions (tickers)")
    quality_score: int = Field(0, description="Initial quality score (0-100)")
    raw: Optional[Any] = Field(None, description="Raw source data (optional)")

    @staticmethod
    def generate_id(source: str, type_: str, timestamp: str, content: Dict[str, Any]) -> str:
        """Generate a unique hash for the event."""
        base = f"{source}|{type_}|{timestamp}|{str(content)}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    @classmethod
    def create(
        cls,
        source: str,
        type_: str,
        timestamp: datetime,
        content: Dict[str, Any],
        raw: Any = None,
        entities: Optional[list[str]] = None,
        quality_score: Optional[int] = None
    ):
        ts = timestamp.replace(microsecond=0).isoformat() + 'Z'  # UTC ISO8601
        eid = cls.generate_id(source, type_, ts, content)
        # Simple scoring: +10 for each entity, +10 for news, +5 for price
        score = quality_score if quality_score is not None else 0
        if entities:
            score += 10 * len(entities)
        if type_ == "news":
            score += 10
        if type_ == "price":
            score += 5
        return cls(id=eid, source=source, type=type_, timestamp=ts, content=content, entities=entities or [], quality_score=score, raw=raw)
