"""
SQLAlchemy models for intelligence pipeline:
- ProcessedEvent: Results from Agent A (Sieve)
- WalletProfileORM, EntityORM, TradeRecordORM: Agent B (Profiler) data
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Index, ARRAY, Boolean, UUID
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.config.db import Base
from datetime import datetime
import uuid


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    id = Column(
        String, primary_key=True
    )  # Store actual event ID (as string from DB schema)
    user_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    priority = Column(String, index=True)
    score = Column(Float)
    multi_source = Column(Integer)
    engagement = Column(Integer)
    bot = Column(Integer)
    dedup = Column(Integer)
    event_data = Column(JSON)  # Store original event + enrichments
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  #  Track Agent B updates

    __table_args__ = (
        Index("ix_priority_timestamp_user", "priority", "timestamp", "user_id"),
    )


# Retention policy: To be enforced by a scheduled cleanup task (not in model)
# Example cleanup query:
# session.query(ProcessedEvent).filter(ProcessedEvent.timestamp < datetime.utcnow() - timedelta(days=7)).delete()


# ============================================================================
# AGENT B (PROFILER) MODELS
# ============================================================================


class WalletProfileORM(Base):
    """Stores wallet profiles with historical performance metrics."""

    __tablename__ = "wallet_profiles"

    wallet_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address = Column(String, unique=True, index=True, nullable=False)
    blockchain = Column(String, default="ethereum")

    # Entity information
    entity_type = Column(String, index=True)  # exchange, whale, vc_fund, etc.
    entity_name = Column(String, index=True)

    # Performance metrics
    total_trades = Column(Integer, default=0)
    profitable_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)  # 0.0 to 1.0
    avg_return_24h = Column(Float, default=0.0)
    avg_return_7d = Column(Float, default=0.0)
    best_trade_return = Column(Float, default=0.0)
    worst_trade_return = Column(Float, default=0.0)

    # Behavioral classification
    behavior_cluster = Column(String)  # accumulator, trader, liquidator, etc.
    tier = Column(String, index=True)  # high_performer, medium_performer, low_performer
    confidence_score = Column(Float, default=0.0)  # 0.0 to 1.0

    # Activity patterns
    activity_frequency = Column(String, default="inactive")  # daily, weekly, monthly
    last_activity = Column(DateTime)
    first_seen = Column(DateTime)

    # Preferences
    preferred_tokens = Column(ARRAY(String), default=[])
    favorite_exchanges = Column(ARRAY(String), default=[])
    favorite_dexes = Column(ARRAY(String), default=[])

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("ix_tier_win_rate", "tier", "win_rate"),)


class EntityORM(Base):
    """Stores entities (real-world persons/organizations) and their linked wallets."""

    __tablename__ = "entities"

    entity_id = Column(String, primary_key=True)
    name = Column(String, index=True, nullable=False)
    entity_type = Column(String, index=True)  # exchange, vc_fund, whale, etc.
    wallets = Column(ARRAY(String), default=[])  # List of controlled addresses

    # Profile
    description = Column(String)
    website = Column(String)
    twitter_handle = Column(String)

    # Verification
    verified = Column(Boolean, default=False, index=True)
    verification_sources = Column(ARRAY(String), default=[])

    # Aggregated metrics
    total_capital_tracked_usd = Column(Float, default=0.0)
    total_transactions = Column(Integer, default=0)
    reliability_score = Column(Float, default=0.0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_entity_verified", "verified"),
        Index("ix_entity_wallets", "wallets"),
    )


class TradeRecordORM(Base):
    """Historical trade records for win rate and pattern analysis."""

    __tablename__ = "trade_records"

    trade_id = Column(String, primary_key=True)
    wallet_address = Column(String, index=True, nullable=False)
    token_in = Column(String, index=True)
    token_out = Column(String, index=True)
    amount_in = Column(Float)
    amount_out = Column(Float)
    usd_value = Column(Float, index=True)
    exchange_or_dex = Column(String, index=True)
    timestamp = Column(DateTime, index=True, nullable=False)

    # Profitability (calculated after outcome known)
    is_profitable = Column(Boolean, index=True)
    return_percentage = Column(Float)  # ROI %
    return_usd = Column(Float)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_wallet_timestamp", "wallet_address", "timestamp"),
        Index("ix_is_profitable", "is_profitable"),
    )


class EntityProfileORM(Base):
    """Aggregated profile of an entity across all wallets (cached)."""

    __tablename__ = "entity_profiles"

    entity_id = Column(String, primary_key=True)
    entity_name = Column(String)
    entity_type = Column(String)

    # Aggregated metrics
    total_wallets = Column(Integer, default=0)
    unique_tokens_traded = Column(Integer, default=0)
    total_trades_across_wallets = Column(Integer, default=0)
    aggregate_win_rate = Column(Float, default=0.0)
    aggregate_profitable_trades = Column(Integer, default=0)

    # Best wallet
    best_wallet = Column(String)
    best_wallet_win_rate = Column(Float)

    # Risk profile
    risk_score = Column(Float, default=0.0)
    prediction_confidence = Column(Float, default=0.0)

    # Historical performance
    performance_last_7d = Column(Float, default=0.0)
    performance_last_30d = Column(Float, default=0.0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
