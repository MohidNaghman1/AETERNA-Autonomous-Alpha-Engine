"""
Event validation schemas using Pydantic.
Ensures data quality and consistency before storage.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import List, Dict, Any, Optional


class ContentSchema(BaseModel):
    """Base content schema - can be extended for specific event types"""
    model_config = ConfigDict(extra="allow")  # Allow additional fields


class RSSContentSchema(ContentSchema):
    """Validation schema for RSS feed events"""
    title: str = Field(..., min_length=5, max_length=500)
    summary: Optional[str] = Field(None, max_length=50000)
    link: str = Field(..., min_length=10)
    published: Optional[str] = None
    source: str = Field(..., min_length=1, max_length=100)
    author: Optional[str] = Field(None, max_length=200)
    categories: Optional[List[str]] = Field(default_factory=list, max_items=20)
    image_url: Optional[str] = Field(None, max_length=500)
    word_count: int = Field(default=0, ge=0)
    read_time_minutes: int = Field(default=0, ge=0, le=1000)
    urls: List[str] = Field(default_factory=list, max_items=50)
    hashtags: List[str] = Field(default_factory=list, max_items=50)
    quality_score: float = Field(default=0.0, ge=0.0, le=100.0)

    @field_validator('title')
    @classmethod
    def title_not_spam(cls, v: str) -> str:
        """Validate title isn't spam-like"""
        if v.count(">>>") > 3 or v.count("!!") > 5:
            raise ValueError("Title looks like spam")
        return v.strip()


class PriceContentSchema(ContentSchema):
    """Validation schema for price feed events"""
    id: str = Field(..., min_length=1, max_length=100)
    symbol: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=200)
    current_price: Optional[float] = Field(None, gt=0)
    ath: Optional[float] = None
    atl: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    market_cap: Optional[float] = None
    market_cap_rank: Optional[int] = Field(None, gt=0)
    trading_volume_24h: Optional[float] = Field(None, ge=0)
    circulating_supply: Optional[float] = Field(None, ge=0)
    
    # Price changes
    change_1h_pct: Optional[float] = Field(None, ge=-100, le=1000)
    change_24h_pct: Optional[float] = Field(None, ge=-100, le=1000)
    change_7d_pct: Optional[float] = Field(None, ge=-100, le=1000)
    change_30d_pct: Optional[float] = Field(None, ge=-100, le=1000)
    risk_score: float = Field(default=50.0, ge=0.0, le=100.0)
    price_volatility_category: str = Field(default="low", pattern="^(low|medium|high)$")

    @field_validator('symbol')
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        """Ensure symbol is uppercase"""
        return v.upper()

    @field_validator('current_price')
    @classmethod
    def current_price_positive(cls, v: Optional[float]) -> Optional[float]:
        """Price must be positive if provided"""
        if v is not None and v <= 0:
            raise ValueError("Current price must be positive")
        return v


class EventSchema(BaseModel):
    """Main event validation schema"""
    model_config = ConfigDict(extra="allow")
    
    source: str = Field(..., min_length=1, max_length=100, description="Event source (rss, coingecko, twitter, etc)")
    type: str = Field(..., min_length=1, max_length=50, description="Event type (news, price, sentiment, etc)")
    timestamp: datetime = Field(..., description="ISO8601 timestamp")
    content: Dict[str, Any] = Field(..., min_length=1, description="Event content")
    entities: List[str] = Field(default_factory=list, max_items=100, description="Extracted entities (crypto names, symbols)")
    raw: Optional[Dict[str, Any]] = Field(None, description="Original raw data")

    @field_validator('timestamp')
    @classmethod
    def timestamp_not_future(cls, v: datetime) -> datetime:
        """Timestamp cannot be in the future"""
        now = datetime.utcnow()
        max_future_seconds = 300  # Allow 5 minutes for clock skew
        
        if v.timestamp() > (now.timestamp() + max_future_seconds):
            raise ValueError(f"Timestamp {v} is in the future")
        return v

    @field_validator('timestamp')
    @classmethod
    def timestamp_not_too_old(cls, v: datetime) -> datetime:
        """Timestamp shouldn't be more than 90 days old"""
        now = datetime.utcnow()
        days_old = (now - v).days
        
        if days_old > 90:
            # Log warning but don't fail - some sources have old data
            pass
        return v

    @field_validator('content')
    @classmethod
    def content_size_limit(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Content shouldn't exceed 1MB when serialized"""
        import json
        size_mb = len(json.dumps(v)) / (1024 * 1024)
        
        if size_mb > 1:
            raise ValueError(f"Content too large: {size_mb:.2f}MB, max 1MB")
        return v

    @field_validator('entities')
    @classmethod
    def entities_not_empty_strings(cls, v: List[str]) -> List[str]:
        """Remove empty strings from entities"""
        return [e.strip() for e in v if e.strip()]

    def validate_by_type(self) -> bool:
        """Perform type-specific validation"""
        try:
            if self.type == "news" and isinstance(self.content, dict):
                # Validate as RSS content
                RSSContentSchema.model_validate(self.content)
            elif self.type == "price" and isinstance(self.content, dict):
                # Validate as price content
                PriceContentSchema.model_validate(self.content)
            return True
        except Exception as e:
            raise ValueError(f"Type-specific validation failed for {self.type}: {str(e)}")


class EventProcessingLogSchema(BaseModel):
    """Schema for event processing audit log"""
    event_id: int = Field(..., gt=0)
    source: str = Field(..., max_length=50)
    status: str = Field(..., pattern="^(pending|processing|success|failed)$")
    error_message: Optional[str] = Field(None, max_length=5000)
    retry_count: int = Field(default=0, ge=0, le=100)
    processed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


def validate_event(event: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate event and return (is_valid, error_message).
    
    Safer than raising exceptions - can be used in pipelines.
    """
    try:
        EventSchema(**event)
        return True, None
    except Exception as e:
        return False, str(e)


def validate_event_strict(event: Dict[str, Any]) -> EventSchema:
    """
    Validate event and return validated object or raise exception.
    
    Use for critical paths where strict validation is needed.
    """
    return EventSchema(**event)
