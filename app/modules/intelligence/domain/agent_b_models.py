"""
Agent B: The Profiler - Domain Models
======================================

Entity identification, wallet clustering, and profiling models for Agent B.
Transforms anonymous blockchain addresses into actionable intelligence about
wallet owners and their trading patterns.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

# ============================================================================
# ENUMS
# ============================================================================


class EntityType(str, Enum):
    """Types of entities that can control wallets."""

    EXCHANGE = "exchange"
    WHALE = "whale"
    VC_FUND = "vc_fund"
    MARKET_MAKER = "market_maker"
    TRADING_BOT = "trading_bot"
    INSTITUTION = "institution"
    UNKNOWN = "unknown"


class WalletTier(str, Enum):
    """Performance tier for whale wallets."""

    HIGH_PERFORMER = "high_performer"  # 80%+ win rate
    MEDIUM_PERFORMER = "medium_performer"  # 50-79% win rate
    LOW_PERFORMER = "low_performer"  # <50% win rate
    UNVERIFIED = "unverified"  # No historical data


class BehaviorCluster(str, Enum):
    """Behavioral patterns for wallet clustering."""

    ACCUMULATOR = "accumulator"  # Buys and holds
    TRADER = "trader"  # Frequent buy/sell
    LIQUIDATOR = "liquidator"  # Moves to exchanges
    ARBITRAGEUR = "arbitrageur"  # Quick swaps
    WHALE = "whale"  # Large movements
    BOT = "bot"  # Automated patterns
    UNKNOWN = "unknown"  # Insufficient data


# ============================================================================
# WALLET MODELS
# ============================================================================


class WalletAddress(BaseModel):
    """Represents a blockchain wallet address."""

    address: str = Field(..., description="Ethereum address (0x...)")
    blockchain: str = Field(default="ethereum", description="Blockchain network")
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "address": "0x7a9f47a94f37e828fe5ab03f2e0199880e6b0b0e",
                "blockchain": "ethereum",
            }
        }


class WalletProfile(BaseModel):
    """Complete profile of a wallet including history and behavior."""

    wallet_id: UUID = Field(default_factory=uuid4)
    address: str
    blockchain: str = "ethereum"

    # Entity information
    entity_type: EntityType = EntityType.UNKNOWN
    entity_name: Optional[str] = None

    # Performance metrics
    total_trades: int = 0
    profitable_trades: int = 0
    win_rate: float = 0.0  # 0.0 to 1.0
    avg_return_24h: float = 0.0  # Average return % in 24h
    avg_return_7d: float = 0.0
    best_trade_return: float = 0.0
    worst_trade_return: float = 0.0

    # Behavioral patterns
    behavior_cluster: BehaviorCluster = BehaviorCluster.UNKNOWN
    tier: WalletTier = WalletTier.UNVERIFIED
    confidence_score: float = 0.0  # 0.0 to 1.0

    # Temporal metrics
    activity_frequency: str = "inactive"  # daily, weekly, monthly
    last_activity: Optional[datetime] = None
    first_seen: Optional[datetime] = None

    # Token preferences (top 5)
    preferred_tokens: List[str] = Field(default_factory=list)

    # Exchange usage patterns
    favorite_exchanges: List[str] = Field(default_factory=list)
    favorite_dexes: List[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "wallet_id": "550e8400-e29b-41d4-a716-446655440000",
                "address": "0x7a9f47a94f37e828fe5ab03f2e0199880e6b0b0e",
                "entity_type": "vc_fund",
                "entity_name": "Andreessen Horowitz",
                "total_trades": 247,
                "profitable_trades": 210,
                "win_rate": 0.85,
                "tier": "high_performer",
            }
        }


class LinkedWallet(BaseModel):
    """Links multiple wallets to the same entity."""

    primary_wallet: str
    secondary_wallets: List[str] = Field(default_factory=list)
    entity_id: Optional[str] = None
    confidence: float = Field(0.9, ge=0.0, le=1.0)

    class Config:
        json_schema_extra = {
            "example": {
                "primary_wallet": "0x7a9f47a94f37e828fe5ab03f2e0199880e6b0b0e",
                "secondary_wallets": ["0x1111....", "0x2222...."],
                "entity_id": "ent_a16z_fund3",
                "confidence": 0.95,
            }
        }


# ============================================================================
# ENTITY MODELS
# ============================================================================


class Entity(BaseModel):
    """Represents a real-world entity (person, DAO, fund, exchange, etc.)."""

    entity_id: str = Field(..., description="Unique entity identifier")
    name: str
    entity_type: EntityType
    wallets: List[str] = Field(
        default_factory=list, description="List of connected wallet addresses"
    )

    # Profile
    description: Optional[str] = None
    website: Optional[str] = None
    twitter_handle: Optional[str] = None

    # Verification
    verified: bool = False
    verification_sources: List[str] = Field(default_factory=list)

    # Metrics
    total_capital_tracked_usd: float = 0.0
    total_transactions: int = 0
    reliability_score: float = 0.0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "entity_id": "ent_a16z_fund3",
                "name": "Andreessen Horowitz Fund III",
                "entity_type": "vc_fund",
                "wallets": ["0x7a9f47a94f37e828fe5ab03f2e0199880e6b0b0e"],
                "verified": True,
            }
        }


class EntityProfile(BaseModel):
    """Aggregated profile of an entity across all wallets."""

    entity_id: str
    entity_name: str
    entity_type: EntityType

    # Aggregated metrics
    total_wallets: int
    unique_tokens_traded: int
    total_trades_across_wallets: int
    aggregate_win_rate: float
    aggregate_profitable_trades: int

    # Best performing wallet
    best_wallet: Optional[str] = None
    best_wallet_win_rate: Optional[float] = None

    # Risk profile
    risk_score: float = 0.0  # 0.0 (low risk) to 1.0 (high risk)
    prediction_confidence: float = 0.0

    # Historical performance
    performance_last_7d: float = 0.0
    performance_last_30d: float = 0.0

    class Config:
        json_schema_extra = {
            "example": {
                "entity_id": "ent_a16z_fund3",
                "entity_name": "Andreessen Horowitz",
                "entity_type": "vc_fund",
                "total_wallets": 5,
                "aggregate_win_rate": 0.85,
                "risk_score": 0.15,
            }
        }


# ============================================================================
# TRADE/TRANSACTION MODELS
# ============================================================================


class TradeRecord(BaseModel):
    """Record of a single trade/transaction."""

    trade_id: str
    wallet_address: str
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    usd_value: float
    exchange_or_dex: str
    timestamp: datetime

    # Outcome (populated later)
    is_profitable: Optional[bool] = None
    return_percentage: Optional[float] = None  # ROI %
    return_usd: Optional[float] = None


# ============================================================================
# PROFILING OUTPUT MODELS
# ============================================================================


class AgentBOutput(BaseModel):
    """Output from Agent B processing an on-chain event."""

    event_id: str
    wallet_address: str
    entity_identified: bool

    # Entity info (if identified)
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    entity_type: Optional[EntityType] = None

    # Wallet profile
    wallet_profile: Optional[WalletProfile] = None

    # Confidence and signals
    confidence_score: float = 0.0
    profiling_signal: str  # "high_performer", "unknown", "suspicious", etc.

    # Alert enrichment
    should_boost_priority: bool = False  # True if high performer
    priority_boost_reason: Optional[str] = None

    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_xyz123",
                "wallet_address": "0x7a9f47a94f37e828fe5ab03f2e0199880e6b0b0e",
                "entity_identified": True,
                "entity_name": "Andreessen Horowitz",
                "entity_type": "vc_fund",
                "confidence_score": 0.95,
                "should_boost_priority": True,
                "priority_boost_reason": "High performer (85% win rate)",
            }
        }


# ============================================================================
# BATCH PROCESSING MODELS
# ============================================================================


class WalletClusteringSummary(BaseModel):
    """Summary of wallet clustering results."""

    total_wallets_analyzed: int
    total_clusters_identified: int
    new_entities_discovered: int
    high_confidence_matches: int
    processing_time_ms: float


class ProfilingBatchResult(BaseModel):
    """Result of processing a batch of events through Agent B."""

    batch_id: str
    total_events_processed: int
    entities_identified: int
    high_priority_events: int
    processing_time_ms: float
    results: List[AgentBOutput]
