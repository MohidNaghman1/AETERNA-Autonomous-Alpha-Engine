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
from sqlalchemy import and_, cast, String, or_
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import ARRAY

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
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


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
    if not wallet_address or not isinstance(wallet_address, str):
        return None

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
    if not wallet_address or not isinstance(wallet_address, str):
        return None

    try:
        entity_orm = (
            db.query(EntityORM)
            .filter(
                EntityORM.wallets.contains([wallet_address.lower()], autoescape=False)
            )
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
    if not wallet_address or not isinstance(wallet_address, str):
        return 0.0, 0, 0

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
    if not wallet_address or not isinstance(wallet_address, str):
        return 0.0, 0.0

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
    if not wallet_address or not isinstance(wallet_address, str):
        return []

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
    if not wallet_address or not isinstance(wallet_address, str):
        return None

    if config is None:
        config = ProfilerConfig()

    try:
        trades = (
            db.query(TradeRecordORM)
            .filter(
                cast(TradeRecordORM.wallet_address, String) == wallet_address.lower()
            )
            .order_by(TradeRecordORM.timestamp.asc())
            .all()
        )

        if not trades:
            return None

        win_rate, profitable_trades, evaluated_trades = calculate_win_rate_from_trades(
            wallet_address, db
        )
        best_trade_return, worst_trade_return = get_best_worst_trades(
            wallet_address, db
        )
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
    if not wallet_address or not isinstance(wallet_address, str):
        return None

    try:
        wallet_lower = wallet_address.lower()
        candidate_rows = (
            db.query(ProcessedEvent)
            .filter(
                or_(
                    ProcessedEvent.event_data["content"]["from_address"].astext()
                    == wallet_lower,
                    ProcessedEvent.event_data["content"]["to_address"].astext()
                    == wallet_lower,
                )
            )
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
            from_matches = (
                isinstance(from_address, str) and from_address.lower() == wallet_lower
            )
            to_matches = (
                isinstance(to_address, str) and to_address.lower() == wallet_lower
            )

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


def infer_entity_from_context(
    wallet_address: str,
    observed_activity: Optional[Dict[str, Any]],
    wallet_profile: Optional[WalletProfile] = None,
) -> Optional[Dict[str, Any]]:
    """Infer a wallet category from repeated behavior without claiming verified ownership."""
    if not wallet_address or not isinstance(wallet_address, str):
        return None

    wallet_lower = wallet_address.lower()
    if wallet_lower == ZERO_ADDRESS:
        return {
            "profiling_signal": "mint_burn_wallet",
            "entity_type": "system_contract",
            "entity_name": "Null / Mint-Burn Address",
            "reason": (
                "This is the Ethereum zero address, commonly used for minting, burning, "
                "and protocol accounting flows rather than a user-owned wallet."
            ),
            "confidence_score": 0.95,
        }

    if not observed_activity:
        return None

    observed_event_count = int(observed_activity.get("observed_event_count", 0) or 0)
    inbound_transfers = int(observed_activity.get("inbound_transfers", 0) or 0)
    outbound_transfers = int(observed_activity.get("outbound_transfers", 0) or 0)
    total_observed_usd = float(observed_activity.get("total_observed_usd", 0) or 0)
    counterparties = observed_activity.get("counterparties", []) or []
    tokens_seen = observed_activity.get("tokens_seen", []) or []

    first_seen_raw = observed_activity.get("first_seen")
    last_seen_raw = observed_activity.get("last_seen")
    first_seen = (
        datetime.fromisoformat(first_seen_raw)
        if isinstance(first_seen_raw, str) and first_seen_raw
        else None
    )
    last_seen = (
        datetime.fromisoformat(last_seen_raw)
        if isinstance(last_seen_raw, str) and last_seen_raw
        else None
    )
    activity_days = (
        max((last_seen - first_seen).total_seconds() / 86400, 1.0)
        if first_seen and last_seen
        else None
    )
    balance_ratio = min(inbound_transfers, outbound_transfers) / max(
        max(inbound_transfers, outbound_transfers), 1
    )

    if (
        observed_event_count >= 100
        and total_observed_usd >= 50_000_000
        and balance_ratio >= 0.75
        and len(counterparties) >= 5
    ):
        return {
            "profiling_signal": "exchange_like",
            "entity_type": EntityType.EXCHANGE.value,
            "entity_name": "Exchange-Like Flow Hub",
            "reason": (
                "High-volume, balanced inbound/outbound transfer flow across many counterparties "
                "resembles exchange-style treasury or hot-wallet behavior."
            ),
            "confidence_score": 0.82,
        }

    if (
        observed_event_count >= 50
        and total_observed_usd >= 10_000_000
        and len(tokens_seen) >= 2
        and balance_ratio >= 0.55
    ):
        return {
            "profiling_signal": "market_maker_like",
            "entity_type": EntityType.MARKET_MAKER.value,
            "entity_name": "Market-Maker-Like Wallet",
            "reason": (
                "The wallet repeatedly moves large value across multiple tokens with a relatively "
                "balanced send/receive pattern, which resembles market-making or routing behavior."
            ),
            "confidence_score": 0.72,
        }

    if total_observed_usd >= 5_000_000 and observed_event_count >= 10:
        return {
            "profiling_signal": "whale_like",
            "entity_type": EntityType.WHALE.value,
            "entity_name": "Whale-Like Wallet",
            "reason": (
                "The wallet has already moved substantial cumulative value in tracked events, "
                "suggesting outsized capital concentration."
            ),
            "confidence_score": 0.68,
        }

    if (
        observed_event_count >= 25
        and activity_days is not None
        and activity_days <= 2
        and len(counterparties) >= 4
    ):
        return {
            "profiling_signal": "bot_like",
            "entity_type": EntityType.TRADING_BOT.value,
            "entity_name": "Bot-Like Wallet",
            "reason": (
                "The wallet appeared frequently in a short time window across several counterparties, "
                "which resembles automated execution behavior."
            ),
            "confidence_score": 0.61,
        }

    if (
        wallet_profile
        and wallet_profile.total_trades >= 20
        and wallet_profile.win_rate >= 0.7
    ):
        return {
            "profiling_signal": "smart_money_like",
            "entity_type": "smart_money_like",
            "entity_name": "Smart-Money-Like Wallet",
            "reason": (
                "Historical trade performance and consistency suggest this wallet behaves like a "
                "strong repeat participant."
            ),
            "confidence_score": 0.66,
        }

    return None


def get_confidence_band(
    confidence_score: float, entity_identified: bool = False
) -> str:
    """Convert a raw confidence score into a user-friendly trust band."""
    if entity_identified or confidence_score >= 0.8:
        return "high"
    if confidence_score >= 0.45:
        return "medium"
    return "low"


def _default_actor_label(profiling_signal: str) -> str:
    """Map internal profiling signals to user-facing actor labels."""
    label_map = {
        "exchange_like": "Likely exchange wallet",
        "market_maker_like": "Likely market maker",
        "whale_like": "Likely whale wallet",
        "smart_money_like": "Likely smart-money wallet",
        "high_performer": "High-performing wallet",
        "medium_performer": "Active wallet",
        "low_performer": "Low-performing wallet",
        "bot_like": "Likely bot-driven wallet",
        "observed_wallet": "Observed repeat-activity wallet",
        "mint_burn_wallet": "Protocol mint/burn wallet",
        "unverified": "Unverified wallet",
        "unknown": "Unclassified wallet",
        "error": "Unavailable wallet profile",
    }
    return label_map.get(profiling_signal, "Unclassified wallet")


def _significance_for_signal(profiling_signal: str) -> str:
    """Explain why a wallet classification matters to an end user."""
    significance_map = {
        "exchange_like": (
            "This often reflects venue treasury or hot-wallet movement, which can hint "
            "at liquidity shifts rather than isolated retail activity."
        ),
        "market_maker_like": (
            "This kind of flow often matches routing or liquidity balancing, which can "
            "matter more for market structure than for directional conviction."
        ),
        "whale_like": (
            "Large transfers tied to capital-concentrated wallets can be worth watching "
            "for follow-on positioning or treasury movement."
        ),
        "smart_money_like": (
            "Strong historical performance can make future moves from this wallet more "
            "interesting to monitor."
        ),
        "high_performer": (
            "This wallet has strong trading history, so its transfers may deserve higher "
            "attention than anonymous baseline flow."
        ),
        "bot_like": (
            "Automated-looking flow may point to execution or routing behavior rather "
            "than discretionary trader intent."
        ),
        "observed_wallet": (
            "The wallet is still unlabeled, but it has appeared often enough to matter "
            "more than a one-off anonymous transfer."
        ),
        "mint_burn_wallet": (
            "This is a protocol/system address, so the transfer may reflect supply or "
            "accounting mechanics instead of a user decision."
        ),
        "unknown": (
            "There is not enough evidence yet to classify this wallet confidently."
        ),
    }
    return significance_map.get(
        profiling_signal,
        "This adds wallet context to an otherwise anonymous transfer.",
    )


def _build_evidence_points(
    profiling_output: AgentBOutput, event_data: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Return compact evidence snippets that support the wallet label."""
    evidence: List[str] = []
    observed_activity = profiling_output.observed_activity or {}
    wallet_profile = profiling_output.wallet_profile

    observed_event_count = observed_activity.get("observed_event_count")
    if isinstance(observed_event_count, int) and observed_event_count > 0:
        evidence.append(f"{observed_event_count} observed transfers")

    total_observed_usd = observed_activity.get("total_observed_usd")
    if isinstance(total_observed_usd, (int, float)) and total_observed_usd > 0:
        evidence.append(f"${float(total_observed_usd):,.0f} observed volume")

    tokens_seen = observed_activity.get("tokens_seen") or []
    if isinstance(tokens_seen, list) and tokens_seen:
        if len(tokens_seen) == 1:
            evidence.append(f"seen moving {tokens_seen[0]}")
        else:
            evidence.append(f"active across {len(tokens_seen)} tracked tokens")

    if wallet_profile and wallet_profile.total_trades > 0:
        evidence.append(f"{wallet_profile.total_trades} historical trades")
        if wallet_profile.win_rate > 0:
            evidence.append(f"{wallet_profile.win_rate:.0%} win rate")

    # For cold-start wallets with no history, extract evidence from this event
    if not evidence and event_data and isinstance(event_data, dict):
        content = event_data.get("content", {})
        if isinstance(content, dict):
            usd_value = content.get("usd_value")
            token = content.get("token") or content.get("token_out")
            if isinstance(usd_value, (int, float)) and usd_value > 0:
                evidence.append(f"${float(usd_value):,.0f} transfer detected")
            if token:
                evidence.append(f"Moving {token}")

    return evidence[:4]


def build_user_facing_profile(
    profiling_output: AgentBOutput,
    role: Optional[str] = None,
    event_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convert raw Agent B output into user-friendly wallet context."""
    profiling_signal = profiling_output.profiling_signal or "unknown"
    role_label = role.capitalize() if role else "Wallet"

    # For cold-start wallets, extract transfer context from event
    transfer_usd_value = 0.0
    if event_data and isinstance(event_data, dict):
        content = event_data.get("content", {})
        if isinstance(content, dict):
            transfer_usd_value = content.get("usd_value", 0.0)

    if profiling_output.entity_identified and profiling_output.entity_name:
        actor_label = profiling_output.entity_name
        actor_type = (
            str(profiling_output.entity_type.value)
            if profiling_output.entity_type
            else "known_entity"
        )
        summary = f"{role_label} is linked to {profiling_output.entity_name}."
    elif profiling_output.inferred_entity_name:
        actor_label = profiling_output.inferred_entity_name
        actor_type = profiling_output.inferred_entity_type or profiling_signal
        summary = (
            f"{role_label} looks like {profiling_output.inferred_entity_name.lower()}."
        )
    else:
        actor_label = _default_actor_label(profiling_signal)
        actor_type = profiling_signal
        if profiling_signal == "observed_wallet":
            summary = f"{role_label} is not labeled yet, but it has repeated tracked activity."
        elif profiling_signal == "unknown":
            # Improve label for cold-start wallets based on transfer amount
            if (
                isinstance(transfer_usd_value, (int, float))
                and transfer_usd_value >= 100000
            ):
                actor_label = "High-value new wallet"
                summary = f"{role_label} is new but moving significant volume in this transfer."
            elif (
                isinstance(transfer_usd_value, (int, float))
                and transfer_usd_value >= 50000
            ):
                actor_label = "Large-transfer new wallet"
                summary = f"{role_label} is new but involved in substantial transfer."
            else:
                summary = f"{role_label} does not have enough evidence to classify yet."
        else:
            summary = f"{role_label} looks like {actor_label.lower()}."

    return {
        "role": role,
        "actor_label": actor_label,
        "actor_type": actor_type,
        "profiling_signal": profiling_signal,
        "trust_level": get_confidence_band(
            profiling_output.confidence_score, profiling_output.entity_identified
        ),
        "summary": summary,
        "significance": _significance_for_signal(profiling_signal),
        "evidence": _build_evidence_points(profiling_output, event_data),
    }


def build_transfer_relationship_summary(
    sender_output: Optional[AgentBOutput],
    receiver_output: Optional[AgentBOutput],
    event_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Summarize the relationship between sender and receiver for the alert user."""
    if not sender_output and not receiver_output:
        return None

    content = event_data.get("content", {}) if isinstance(event_data, dict) else {}
    if not isinstance(content, dict):
        content = {}

    sender_context = (
        build_user_facing_profile(sender_output, role="sender", event_data=event_data)
        if sender_output
        else None
    )
    receiver_context = (
        build_user_facing_profile(
            receiver_output, role="receiver", event_data=event_data
        )
        if receiver_output
        else None
    )

    sender_label = (
        sender_context["actor_label"] if sender_context else "Unclassified sender"
    )
    receiver_label = (
        receiver_context["actor_label"] if receiver_context else "Unclassified receiver"
    )

    # Extract asset info from event
    asset_label = (
        content.get("token")
        or content.get("token_out")
        or content.get("token_in")
        or "assets"
    )
    usd_value = content.get("usd_value", 0.0)

    sender_signal = sender_output.profiling_signal if sender_output else "unknown"
    receiver_signal = receiver_output.profiling_signal if receiver_output else "unknown"

    if sender_signal == "unknown" and receiver_signal == "unknown":
        return None

    liquidity_signals = {
        "exchange_like",
        "market_maker_like",
        "bot_like",
        "mint_burn_wallet",
    }
    capital_signals = {"whale_like", "smart_money_like", "high_performer"}

    is_actionable = False

    if sender_signal in liquidity_signals and receiver_signal in liquidity_signals:
        # Operational Liquidity
        is_actionable = False
        if isinstance(usd_value, (int, float)) and usd_value > 0:
            summary = (
                f"{sender_label} routed {asset_label} worth ${float(usd_value):,.0f} "
                f"to {receiver_label}."
            )
        else:
            summary = f"{sender_label} routed {asset_label} to {receiver_label}."
        significance = (
            "This appears to be routine operational liquidity movement "
            "between infrastructure or automated wallets."
        )

    elif sender_signal in capital_signals and receiver_signal in liquidity_signals:
        # Deposit
        is_actionable = True
        if isinstance(usd_value, (int, float)) and usd_value > 0:
            summary = (
                f"{sender_label} deposited {asset_label} worth ${float(usd_value):,.0f} "
                f"to {receiver_label}."
            )
        else:
            summary = f"{sender_label} deposited {asset_label} to {receiver_label}."
        significance = (
            "A major capital-holder is moving funds to an active liquidity venue, "
            "possibly preparing to sell, trade, or deploy capital."
        )

    elif sender_signal in liquidity_signals and receiver_signal in capital_signals:
        # Withdrawal
        is_actionable = True
        if isinstance(usd_value, (int, float)) and usd_value > 0:
            summary = (
                f"{sender_label} withdrew {asset_label} worth ${float(usd_value):,.0f} "
                f"to {receiver_label}."
            )
        else:
            summary = f"{sender_label} withdrew {asset_label} to {receiver_label}."
        significance = (
            "A major capital-holder is withdrawing funds from a liquidity venue, "
            "often a sign of accumulation or secure storage."
        )

    elif sender_signal in capital_signals or receiver_signal in capital_signals:
        # Capital movement
        is_actionable = True
        if isinstance(usd_value, (int, float)) and usd_value > 0:
            summary = (
                f"{sender_label} sent {asset_label} worth ${float(usd_value):,.0f} "
                f"to {receiver_label}."
            )
        else:
            summary = f"{sender_label} sent {asset_label} to {receiver_label}."
        significance = (
            "A large transfer involving a high-capital wallet; tracking this "
            "could reveal significant directional intent."
        )

    else:
        # Generic mixed or single unknown
        is_actionable = False
        if isinstance(usd_value, (int, float)) and usd_value > 0:
            summary = (
                f"{sender_label} sent {asset_label} worth ${float(usd_value):,.0f} "
                f"to {receiver_label}."
            )
        else:
            summary = f"{sender_label} sent {asset_label} to {receiver_label}."
        significance = (
            "At least one side of the transfer has tracked activity, adding some context, "
            "though clear directional intent is uncertain."
        )

    return {
        "summary": summary,
        "significance": significance,
        "sender_label": sender_label,
        "receiver_label": receiver_label,
        "is_actionable": is_actionable,
    }


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
            wallet_profile = build_wallet_profile_from_trades(
                wallet_address, db, config
            )

        inferred_entity = infer_entity_from_context(
            wallet_address=wallet_address,
            observed_activity=observed_activity,
            wallet_profile=wallet_profile,
        )
        if inferred_entity:
            output.inferred_entity_type = inferred_entity["entity_type"]
            output.inferred_entity_name = inferred_entity["entity_name"]
            output.inferred_entity_reason = inferred_entity["reason"]

        if wallet_profile is None:
            logger.debug(f"Wallet {wallet_address} has no profile or trade history")
            if inferred_entity:
                output.profiling_signal = inferred_entity["profiling_signal"]
                output.confidence_score = inferred_entity["confidence_score"]
            elif (
                observed_activity
                and observed_activity.get("observed_event_count", 0) >= 2
            ):
                output.profiling_signal = "observed_wallet"
                output.confidence_score = min(
                    0.15 + (observed_activity["observed_event_count"] * 0.02), 0.4
                )
            elif entity:
                output.profiling_signal = "unverified"
                output.confidence_score = calculate_confidence_score(
                    total_trades=0,
                    wallet_verified=False,
                    entity_verified=entity.verified,
                    config=config,
                )
            else:
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
        if wallet_profile.total_trades == 0 and wallet_profile.entity_type != "unknown":
            # Use entity_type if wallet has been identified but has no trades yet
            entity_type_map = {
                "whale": "whale_like",
                "exchange": "exchange_like",
                "market_maker": "market_maker_like",
                "trading_bot": "bot_like",
                "system_contract": "mint_burn_wallet",
            }
            output.profiling_signal = entity_type_map.get(
                wallet_profile.entity_type, "unverified"
            )
            logger.debug(
                f"Using entity type '{wallet_profile.entity_type}' as profiling signal for {wallet_address}"
            )
        elif tier == WalletTier.HIGH_PERFORMER:
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

        if (
            not entity
            and inferred_entity
            and output.profiling_signal
            in {
                "unverified",
                "low_performer",
                "medium_performer",
            }
        ):
            output.inferred_entity_type = inferred_entity["entity_type"]
            output.inferred_entity_name = inferred_entity["entity_name"]
            output.inferred_entity_reason = inferred_entity["reason"]

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
        "inferred_entity_name": profiling_output.inferred_entity_name,
        "inferred_entity_type": profiling_output.inferred_entity_type,
        "inferred_entity_reason": profiling_output.inferred_entity_reason,
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
