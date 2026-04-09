"""
Agent B - The Profiler (Wallet Entity Identification & Profiling)
================================================================

Enriches on-chain and other events with wallet profiling data:
- Wallet entity identification (who controls this address?)
- Historical trading performance analysis (win rate, best trades)
- Behavioral clustering (accumulator, trader, liquidator, etc.)
- Priority boosting for high-performer wallets

Data Flow:
  Event (with wallet address)
    → Agent B lookup & profiling
    → AgentBOutput (enriched event with entity/wallet info)
    → Higher priority for high performers
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import json
import logging
from sqlalchemy import and_, cast, String
from sqlalchemy.orm import Session

from app.modules.intelligence.domain.agent_b_models import (
    WalletProfile,
    WalletTier,
    EntityType,
    BehaviorCluster,
    Entity,
    EntityProfile,
    AgentBOutput,
    TradeRecord,
)
from app.modules.intelligence.infrastructure.models import (
    ProcessedEvent,
    WalletProfileORM,
    EntityORM,
    TradeRecordORM,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================


class ProfilerConfig:
    """Configuration for Agent B profiling logic."""

    # Win rate thresholds for tier classification
    HIGH_PERFORMER_THRESHOLD = 0.80  # 80%+
    MEDIUM_PERFORMER_THRESHOLD = 0.50  # 50-79%
    LOW_PERFORMER_THRESHOLD = 0.0  # <50%

    # Minimum trades needed to calculate meaningful win rate
    MIN_TRADES_FOR_VERIFICATION = 5
    MIN_TRADES_FOR_CONFIDENCE = 20

    # Confidence scoring
    BASE_CONFIDENCE = 0.5
    CONFIDENCE_PER_TRADE = 0.01  # +1% confidence per trade (max 10 trades = 60%)
    VERIFIED_WALLET_BOOST = 0.1  # +10% if wallet has enough verified history
    VERIFIED_ENTITY_BOOST = 0.2  # +20% if entity is verified

    # Behavior clustering thresholds
    ACCUMULATOR_THRESHOLD = 0.7  # 70%+ in one token
    LIQUIDATOR_THRESHOLD = 0.5  # Moving to exchanges frequently
    ARBITRAGEUR_THRESHOLD_TIME = 3600  # Trades within 1 hour are arbs
    BOT_PATTERN_THRESHOLD = 0.8  # 80%+ regular intervals

    # Risk scoring
    HIGH_PERFORMER_RISK = 0.2  # Lower risk
    MEDIUM_PERFORMER_RISK = 0.5
    LOW_PERFORMER_RISK = 0.8  # Higher risk
    UNKNOWN_WALLET_RISK = 0.7


# ============================================================================
# WALLET LOOKUP
# ============================================================================


def lookup_wallet_profile(wallet_address: str, db: Session) -> Optional[WalletProfile]:
    """
    Look up a wallet profile from the database.

    Args:
        wallet_address: Ethereum address (0x...)
        db: Database session

    Returns:
        WalletProfile if found, None otherwise
    """
    try:
        # Query wallet from ORM
        wallet_orm = (
            db.query(WalletProfileORM)
            .filter(cast(WalletProfileORM.address, String) == wallet_address.lower())
            .first()
        )

        if not wallet_orm:
            logger.debug(f"Wallet not found: {wallet_address}")
            return None

        # Convert ORM to Pydantic model
        profile = WalletProfile(
            wallet_id=wallet_orm.wallet_id,
            address=wallet_orm.address,
            blockchain=wallet_orm.blockchain,
            entity_type=EntityType(wallet_orm.entity_type),
            entity_name=wallet_orm.entity_name,
            total_trades=wallet_orm.total_trades,
            profitable_trades=wallet_orm.profitable_trades,
            win_rate=wallet_orm.win_rate,
            avg_return_24h=wallet_orm.avg_return_24h,
            avg_return_7d=wallet_orm.avg_return_7d,
            best_trade_return=wallet_orm.best_trade_return,
            worst_trade_return=wallet_orm.worst_trade_return,
            behavior_cluster=BehaviorCluster(wallet_orm.behavior_cluster),
            tier=WalletTier(wallet_orm.tier),
            confidence_score=wallet_orm.confidence_score,
            activity_frequency=wallet_orm.activity_frequency,
            last_activity=wallet_orm.last_activity,
            first_seen=wallet_orm.first_seen,
            preferred_tokens=wallet_orm.preferred_tokens or [],
            favorite_exchanges=wallet_orm.favorite_exchanges or [],
            favorite_dexes=wallet_orm.favorite_dexes or [],
        )
        logger.debug(
            f"Found wallet profile: {wallet_address} (win_rate={profile.win_rate})"
        )
        return profile

    except Exception as e:
        logger.error(f"Error looking up wallet {wallet_address}: {e}")
        return None


def lookup_entity_by_wallet(wallet_address: str, db: Session) -> Optional[Entity]:
    """
    Look up entity information by wallet address.

    Args:
        wallet_address: Ethereum address
        db: Database session

    Returns:
        Entity info if found, None otherwise
    """
    try:
        entity_orm = (
            db.query(EntityORM)
            .filter(EntityORM.wallets.contains([wallet_address.lower()]))
            .first()
        )

        if not entity_orm:
            logger.debug(f"No entity found for wallet: {wallet_address}")
            return None

        entity = Entity(
            entity_id=entity_orm.entity_id,
            name=entity_orm.name,
            entity_type=EntityType(entity_orm.entity_type),
            wallets=entity_orm.wallets,
            description=entity_orm.description,
            website=entity_orm.website,
            twitter_handle=entity_orm.twitter_handle,
            verified=entity_orm.verified,
            verification_sources=entity_orm.verification_sources or [],
            total_capital_tracked_usd=entity_orm.total_capital_tracked_usd,
            total_transactions=entity_orm.total_transactions,
            reliability_score=entity_orm.reliability_score,
        )
        logger.debug(f"Found entity for wallet {wallet_address}: {entity.name}")
        return entity

    except Exception as e:
        logger.error(f"Error looking up entity for wallet {wallet_address}: {e}")
        return None


# ============================================================================
# HISTORICAL ANALYSIS
# ============================================================================


def calculate_win_rate_from_trades(
    wallet_address: str, db: Session, days: int = 90
) -> Tuple[float, int, int]:
    """
    Calculate win rate from historical trades.

    Args:
        wallet_address: Wallet to analyze
        db: Database session
        days: How many days to look back (default 90)

    Returns:
        (win_rate: float, profitable_trades: int, total_trades: int)
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        trades = (
            db.query(TradeRecordORM)
            .filter(
                and_(
                    cast(TradeRecordORM.wallet_address, String)
                    == wallet_address.lower(),
                    TradeRecordORM.timestamp >= cutoff_date,
                    TradeRecordORM.is_profitable.isnot(None),
                )
            )
            .all()
        )

        if not trades:
            logger.debug(f"No trades found for {wallet_address} in last {days} days")
            return 0.0, 0, 0

        profitable = sum(1 for t in trades if t.is_profitable)
        total = len(trades)
        win_rate = profitable / total if total > 0 else 0.0

        logger.debug(
            f"Calculated win rate for {wallet_address}: {win_rate:.2%} "
            f"({profitable}/{total} trades)"
        )
        return win_rate, profitable, total

    except Exception as e:
        logger.error(f"Error calculating win rate for {wallet_address}: {e}")
        return 0.0, 0, 0


def get_best_worst_trades(
    wallet_address: str, db: Session, days: int = 90
) -> Tuple[float, float]:
    """
    Find best and worst trade returns.

    Args:
        wallet_address: Wallet to analyze
        db: Database session
        days: Lookback period

    Returns:
        (best_return: float, worst_return: float)
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        trades = (
            db.query(TradeRecordORM)
            .filter(
                and_(
                    cast(TradeRecordORM.wallet_address, String)
                    == wallet_address.lower(),
                    TradeRecordORM.timestamp >= cutoff_date,
                    TradeRecordORM.return_percentage.isnot(None),
                )
            )
            .all()
        )

        if not trades:
            return 0.0, 0.0

        returns = [
            t.return_percentage for t in trades if t.return_percentage is not None
        ]
        best = max(returns) if returns else 0.0
        worst = min(returns) if returns else 0.0

        return best, worst

    except Exception as e:
        logger.error(f"Error getting best/worst trades for {wallet_address}: {e}")
        return 0.0, 0.0


def get_preferred_tokens(
    wallet_address: str, db: Session, days: int = 90, limit: int = 5
) -> List[str]:
    """
    Get the most frequently traded tokens for a wallet.

    Args:
        wallet_address: Wallet to analyze
        db: Database session
        days: Lookback period
        limit: Max tokens to return

    Returns:
        List of token addresses (most frequent first)
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Query trades for this wallet
        trades = (
            db.query(TradeRecordORM)
            .filter(
                and_(
                    cast(TradeRecordORM.wallet_address, String)
                    == wallet_address.lower(),
                    TradeRecordORM.timestamp >= cutoff_date,
                )
            )
            .all()
        )

        if not trades:
            return []

        # Count token occurrences (in + out)
        token_counts: Dict[str, int] = {}
        for trade in trades:
            token_counts[trade.token_in] = token_counts.get(trade.token_in, 0) + 1
            token_counts[trade.token_out] = token_counts.get(trade.token_out, 0) + 1

        # Sort by frequency and return top N
        sorted_tokens = sorted(token_counts.items(), key=lambda x: x[1], reverse=True)
        preferred = [token for token, count in sorted_tokens[:limit]]

        return preferred

    except Exception as e:
        logger.error(f"Error getting preferred tokens for {wallet_address}: {e}")
        return []


def infer_activity_frequency(
    first_seen: Optional[datetime], last_seen: Optional[datetime], total_trades: int
) -> str:
    """Infer a coarse activity cadence from observed trade history."""
    if not first_seen or not last_seen or total_trades <= 0:
        return "inactive"

    span_days = max((last_seen - first_seen).total_seconds() / 86400, 1.0)
    trades_per_day = total_trades / span_days

    if trades_per_day >= 1:
        return "daily"
    if trades_per_day * 7 >= 1:
        return "weekly"
    return "monthly"


def build_wallet_profile_from_trades(
    wallet_address: str, db: Session, config: Optional[ProfilerConfig] = None
) -> Optional[WalletProfile]:
    """Synthesize a lightweight wallet profile directly from trade history."""
    if config is None:
        config = ProfilerConfig()

    try:
        trades = (
            db.query(TradeRecordORM)
            .filter(cast(TradeRecordORM.wallet_address, String) == wallet_address.lower())
            .order_by(TradeRecordORM.timestamp.asc())
            .all()
        )

        if not trades:
            return None

        win_rate, profitable_trades, evaluated_trades = calculate_win_rate_from_trades(
            wallet_address, db
        )
        best_trade_return, worst_trade_return = get_best_worst_trades(wallet_address, db)
        preferred_tokens = get_preferred_tokens(wallet_address, db)

        first_seen = trades[0].timestamp
        last_seen = trades[-1].timestamp
        total_trades = evaluated_trades or len(trades)
        tier = classify_wallet_tier(win_rate, total_trades, config)

        profile = WalletProfile(
            address=wallet_address.lower(),
            blockchain="ethereum",
            total_trades=total_trades,
            profitable_trades=profitable_trades,
            win_rate=win_rate,
            best_trade_return=best_trade_return,
            worst_trade_return=worst_trade_return,
            behavior_cluster=BehaviorCluster.UNKNOWN,
            tier=tier,
            activity_frequency=infer_activity_frequency(
                first_seen=first_seen,
                last_seen=last_seen,
                total_trades=len(trades),
            ),
            last_activity=last_seen,
            first_seen=first_seen,
            preferred_tokens=preferred_tokens,
            favorite_exchanges=[],
            favorite_dexes=[],
        )
        logger.debug(
            f"Built fallback wallet profile from trades for {wallet_address}: "
            f"{total_trades} trades, signal={tier}"
        )
        return profile

    except Exception as e:
        logger.error(f"Error building fallback profile for {wallet_address}: {e}")
        return None


def extract_counterparty_address(
    wallet_address: str, event_data: Dict[str, Any]
) -> Optional[str]:
    """Return the other side of an on-chain transfer when available."""
    content = event_data.get("content", {}) if isinstance(event_data, dict) else {}
    if not isinstance(content, dict):
        return None

    from_address = content.get("from_address")
    to_address = content.get("to_address")
    wallet_lower = (wallet_address or "").lower()

    if isinstance(from_address, str) and from_address.lower() == wallet_lower:
        return to_address.lower() if isinstance(to_address, str) else to_address
    if isinstance(to_address, str) and to_address.lower() == wallet_lower:
        return from_address.lower() if isinstance(from_address, str) else from_address
    return None


def summarize_wallet_observations(
    wallet_address: str, db: Session, limit: int = 200
) -> Optional[Dict[str, Any]]:
    """Build a lightweight observed-activity summary from processed events."""
    try:
        candidate_rows = (
            db.query(ProcessedEvent)
            .filter(cast(ProcessedEvent.event_data, String).ilike(f"%{wallet_address.lower()}%"))
            .order_by(ProcessedEvent.timestamp.desc())
            .limit(limit)
            .all()
        )

        if not candidate_rows:
            return None

        observed_event_count = 0
        inbound_transfers = 0
        outbound_transfers = 0
        total_observed_usd = 0.0
        tokens = set()
        counterparties = set()
        first_seen = None
        last_seen = None
        wallet_lower = wallet_address.lower()

        for row in candidate_rows:
            event_data = row.event_data
            if isinstance(event_data, str):
                try:
                    event_data = json.loads(event_data)
                except json.JSONDecodeError:
                    continue
            if not isinstance(event_data, dict):
                continue

            content = event_data.get("content", {})
            if not isinstance(content, dict):
                continue

            from_address = content.get("from_address")
            to_address = content.get("to_address")
            from_matches = isinstance(from_address, str) and from_address.lower() == wallet_lower
            to_matches = isinstance(to_address, str) and to_address.lower() == wallet_lower

            if not (from_matches or to_matches):
                continue

            observed_event_count += 1
            if from_matches:
                outbound_transfers += 1
                if isinstance(to_address, str):
                    counterparties.add(to_address.lower())
            if to_matches:
                inbound_transfers += 1
                if isinstance(from_address, str):
                    counterparties.add(from_address.lower())

            usd_value = content.get("usd_value")
            if isinstance(usd_value, (int, float)):
                total_observed_usd += float(usd_value)

            token = content.get("token")
            if isinstance(token, str) and token:
                tokens.add(token)

            row_ts = row.timestamp
            if row_ts and (last_seen is None or row_ts > last_seen):
                last_seen = row_ts
            if row_ts and (first_seen is None or row_ts < first_seen):
                first_seen = row_ts

        if observed_event_count == 0:
            return None

        return {
            "observed_event_count": observed_event_count,
            "inbound_transfers": inbound_transfers,
            "outbound_transfers": outbound_transfers,
            "total_observed_usd": round(total_observed_usd, 2),
            "tokens_seen": sorted(tokens)[:5],
            "counterparties": sorted(counterparties)[:5],
            "first_seen": first_seen.isoformat() if first_seen else None,
            "last_seen": last_seen.isoformat() if last_seen else None,
        }

    except Exception as e:
        logger.error(f"Error summarizing observations for {wallet_address}: {e}")
        return None


# ============================================================================
# TIER & BEHAVIOR CLASSIFICATION
# ============================================================================


def classify_wallet_tier(
    win_rate: float, total_trades: int, config: Optional[ProfilerConfig] = None
) -> WalletTier:
    """
    Classify wallet performance tier based on win rate and trade history.

    Args:
        win_rate: Historical win rate (0.0-1.0)
        total_trades: Total trades executed
        config: Configuration object

    Returns:
        WalletTier enum
    """
    if config is None:
        config = ProfilerConfig()

    # Need minimum trades for classification
    if total_trades < config.MIN_TRADES_FOR_VERIFICATION:
        return WalletTier.UNVERIFIED

    if win_rate >= config.HIGH_PERFORMER_THRESHOLD:
        return WalletTier.HIGH_PERFORMER
    elif win_rate >= config.MEDIUM_PERFORMER_THRESHOLD:
        return WalletTier.MEDIUM_PERFORMER
    else:
        return WalletTier.LOW_PERFORMER


def classify_behavior_cluster(
    wallet_profile: WalletProfile,
    favorite_exchanges: List[str],
    db: Session,
    config: Optional[ProfilerConfig] = None,
) -> BehaviorCluster:
    """
    Classify wallet behavior pattern.

    Args:
        wallet_profile: Wallet profile
        favorite_exchanges: List of favorite exchanges
        db: Database session
        config: Configuration

    Returns:
        BehaviorCluster enum
    """
    if config is None:
        config = ProfilerConfig()

    # Need enough history
    if wallet_profile.total_trades < 5:
        return BehaviorCluster.UNKNOWN

    # Liquidator: frequently moves to exchanges
    if favorite_exchanges and len(wallet_profile.favorite_exchanges) > 0:
        exchange_ratio = len(favorite_exchanges) / max(
            1, len(favorite_exchanges) + len(wallet_profile.favorite_dexes)
        )
        if exchange_ratio > config.LIQUIDATOR_THRESHOLD:
            return BehaviorCluster.LIQUIDATOR

    # Accumulator: high win rate + concentrated in few tokens
    if (
        wallet_profile.win_rate >= config.HIGH_PERFORMER_THRESHOLD
        and len(wallet_profile.preferred_tokens) <= 3
    ):
        return BehaviorCluster.ACCUMULATOR

    # Trader: medium-high frequency, diverse tokens
    if wallet_profile.activity_frequency in ["daily", "weekly"]:
        if len(wallet_profile.preferred_tokens) > 3:
            if wallet_profile.win_rate >= 0.5:
                return BehaviorCluster.TRADER

    # Whale: large movements, infrequent
    if (
        wallet_profile.avg_return_24h > 0.05
        and wallet_profile.activity_frequency == "monthly"
    ):
        return BehaviorCluster.WHALE

    # Default to unknown if none match
    return BehaviorCluster.UNKNOWN


def calculate_confidence_score(
    total_trades: int,
    wallet_verified: bool = False,
    entity_verified: bool = False,
    config: Optional[ProfilerConfig] = None,
) -> float:
    """
    Calculate confidence score for wallet profiling.

    Args:
        total_trades: Number of historical trades
        wallet_verified: Is wallet verified
        entity_verified: Is entity verified
        config: Configuration

    Returns:
        Confidence score (0.0-1.0)
    """
    if config is None:
        config = ProfilerConfig()

    # Base confidence
    confidence = config.BASE_CONFIDENCE

    # Add confidence per trade (up to 20 trades)
    confidence += min(total_trades * config.CONFIDENCE_PER_TRADE, 0.1)

    # Verified wallet history boost
    if wallet_verified:
        confidence += config.VERIFIED_WALLET_BOOST

    # Entity verification boost
    if entity_verified:
        confidence += config.VERIFIED_ENTITY_BOOST

    # Cap at 1.0
    return min(confidence, 1.0)


# ============================================================================
# MAIN PROFILING LOGIC
# ============================================================================


def profile_wallet_from_event(
    wallet_address: str,
    event_id: str,
    event_data: Dict[str, Any],
    db: Session,
    config: Optional[ProfilerConfig] = None,
) -> AgentBOutput:
    """
    Main profiling function: enriches an event with wallet profiling data.

    Args:
        wallet_address: Ethereum address to profile
        event_id: Event ID (from on-chain collector or other source)
        event_data: Event content dictionary
        db: Database session
        config: Configuration

    Returns:
        AgentBOutput with profiling results
    """
    if config is None:
        config = ProfilerConfig()

    output = AgentBOutput(
        event_id=event_id,
        wallet_address=wallet_address,
        entity_identified=False,
        counterparty_address=extract_counterparty_address(wallet_address, event_data),
        confidence_score=0.0,
        profiling_signal="unknown",
        should_boost_priority=False,
    )

    try:
        observed_activity = summarize_wallet_observations(wallet_address, db)
        if observed_activity:
            output.observed_activity = observed_activity

        # Lookup entity
        entity = lookup_entity_by_wallet(wallet_address, db)

        if entity:
            output.entity_identified = True
            output.entity_id = entity.entity_id
            output.entity_name = entity.name
            output.entity_type = entity.entity_type

        # Lookup wallet profile
        wallet_profile = lookup_wallet_profile(wallet_address, db)
        if wallet_profile is None:
            wallet_profile = build_wallet_profile_from_trades(wallet_address, db, config)

        if wallet_profile is None:
            logger.debug(f"Wallet {wallet_address} has no profile or trade history")
            if observed_activity and observed_activity.get("observed_event_count", 0) >= 2:
                output.profiling_signal = "observed_wallet"
                output.confidence_score = min(
                    0.15 + (observed_activity["observed_event_count"] * 0.02), 0.4
                )
            if entity:
                output.profiling_signal = "unverified"
                output.confidence_score = calculate_confidence_score(
                    total_trades=0,
                    wallet_verified=False,
                    entity_verified=entity.verified,
                    config=config,
                )
            elif output.profiling_signal != "observed_wallet":
                output.profiling_signal = "unknown"
            return output

        # Set wallet profile
        output.wallet_profile = wallet_profile

        # Classify tier
        tier = classify_wallet_tier(
            wallet_profile.win_rate, wallet_profile.total_trades, config
        )

        # Calculate confidence
        confidence = calculate_confidence_score(
            wallet_profile.total_trades,
            wallet_verified=(tier != WalletTier.UNVERIFIED),
            entity_verified=(entity and entity.verified),
            config=config,
        )
        output.confidence_score = confidence
        output.wallet_profile.tier = tier
        output.wallet_profile.confidence_score = confidence
        if output.wallet_profile.behavior_cluster == BehaviorCluster.UNKNOWN:
            output.wallet_profile.behavior_cluster = classify_behavior_cluster(
                output.wallet_profile,
                output.wallet_profile.favorite_exchanges,
                db,
                config,
            )

        # Determine profiling signal
        if tier == WalletTier.HIGH_PERFORMER:
            output.profiling_signal = "high_performer"
            output.should_boost_priority = True
            output.priority_boost_reason = (
                f"High performer ({wallet_profile.win_rate:.1%} win rate)"
            )
        elif tier == WalletTier.MEDIUM_PERFORMER:
            output.profiling_signal = "medium_performer"
        elif tier == WalletTier.LOW_PERFORMER:
            output.profiling_signal = "low_performer"
        else:
            output.profiling_signal = "unverified"

        logger.info(
            f"[AGENT B] Profiled {wallet_address}: {output.profiling_signal} "
            f"(confidence={confidence:.2%}, tier={tier})"
        )
        return output

    except Exception as e:
        logger.error(f"[AGENT B] Error profiling wallet {wallet_address}: {e}")
        output.profiling_signal = "error"
        return output


def profile_batch(
    events: List[Dict[str, Any]], db: Session, config: Optional[ProfilerConfig] = None
) -> List[AgentBOutput]:
    """
    Profile a batch of events.

    Args:
        events: List of event dictionaries (must have wallet_address or address field)
        db: Database session
        config: Configuration

    Returns:
        List of AgentBOutput results
    """
    results = []
    for event in events:
        wallet_addr = event.get("wallet_address") or event.get("address")
        if not wallet_addr:
            logger.warning(f"Event {event.get('id', 'unknown')} missing wallet address")
            continue

        output = profile_wallet_from_event(
            wallet_address=wallet_addr,
            event_id=event.get("id", "unknown"),
            event_data=event,
            db=db,
            config=config,
        )
        results.append(output)

    return results


# ============================================================================
# ENRICHMENT FOR DOWNSTREAM AGENTS
# ============================================================================


def enrich_event_with_profiling(
    event: Dict[str, Any],
    profiling_output: AgentBOutput,
) -> Dict[str, Any]:
    """
    Add Agent B profiling data to an event for downstream processing.

    Args:
        event: Original event dict
        profiling_output: AgentBOutput from profiling

    Returns:
        Enriched event dict with agent_b field
    """
    enriched_event = event.copy()

    enriched_event["agent_b"] = {
        "wallet_address": profiling_output.wallet_address,
        "counterparty_address": profiling_output.counterparty_address,
        "entity_identified": profiling_output.entity_identified,
        "entity_id": profiling_output.entity_id,
        "entity_name": profiling_output.entity_name,
        "entity_type": (
            str(profiling_output.entity_type) if profiling_output.entity_type else None
        ),
        "wallet_win_rate": (
            profiling_output.wallet_profile.win_rate
            if profiling_output.wallet_profile
            else None
        ),
        "wallet_tier": (
            str(profiling_output.wallet_profile.tier)
            if profiling_output.wallet_profile
            else None
        ),
        "wallet_profile": (
            profiling_output.wallet_profile.model_dump(mode="json")
            if profiling_output.wallet_profile
            else None
        ),
        "observed_activity": profiling_output.observed_activity,
        "confidence_score": profiling_output.confidence_score,
        "profiling_signal": profiling_output.profiling_signal,
        "should_boost_priority": profiling_output.should_boost_priority,
        "priority_boost_reason": profiling_output.priority_boost_reason,
    }

    return enriched_event
