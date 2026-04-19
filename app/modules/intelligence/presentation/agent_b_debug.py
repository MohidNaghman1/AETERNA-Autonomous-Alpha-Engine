"""
Agent B Debug Endpoints - View all profiling data from database tables

Provides endpoints to inspect all Agent B related data:
- WalletProfiles: Individual wallet profiling records
- Entities: Real-world entities (exchanges, whales, etc.)
- TradeRecords: Historical trades per wallet
- EntityProfiles: Aggregated entity data
- ProcessedEvents: Events with embedded agent_b profiling
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from app.shared.application.dependencies import get_db
from app.modules.intelligence.infrastructure.models import (
    WalletProfileORM,
    EntityORM,
    TradeRecordORM,
    EntityProfileORM,
    ProcessedEvent,
)
from app.modules.intelligence.application.trade_records import (
    get_trade_resolution_snapshot,
    run_trade_outcome_resolution,
    extract_trade_record_payload,
)
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json
from fastapi.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debug/agent-b", tags=["agent-b-debug"])


# ============================================================================
# WALLET PROFILES ENDPOINTS
# ============================================================================


@router.get("/wallet-profiles", response_model=List[Dict[str, Any]])
async def get_wallet_profiles(
    limit: int = Query(100, ge=1, le=1000),
    blockchain: str = Query("ethereum", description="Filter by blockchain"),
    tier: Optional[str] = Query(
        None, description="Filter by tier (high_performer, etc)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all wallet profiles from database.

    Returns complete wallet profiling records including:
    - Wallet address & blockchain
    - Entity classification (whale, market_maker, etc.)
    - Performance metrics (win rate, returns, etc.)
    - Activity patterns
    - Metadata (created_at, updated_at)
    """
    try:
        query = select(WalletProfileORM).where(
            WalletProfileORM.blockchain == blockchain
        )

        if tier:
            query = query.where(WalletProfileORM.tier == tier)

        query = query.order_by(desc(WalletProfileORM.updated_at)).limit(limit)

        result = await db.execute(query)
        profiles = result.scalars().all()

        data = []
        for profile in profiles:
            data.append(
                {
                    "wallet_id": str(profile.wallet_id),
                    "address": profile.address,
                    "blockchain": profile.blockchain,
                    "entity_type": profile.entity_type,
                    "entity_name": profile.entity_name,
                    "total_trades": profile.total_trades,
                    "profitable_trades": profile.profitable_trades,
                    "win_rate": profile.win_rate,
                    "avg_return_24h": profile.avg_return_24h,
                    "avg_return_7d": profile.avg_return_7d,
                    "best_trade_return": profile.best_trade_return,
                    "worst_trade_return": profile.worst_trade_return,
                    "behavior_cluster": profile.behavior_cluster,
                    "tier": profile.tier,
                    "confidence_score": profile.confidence_score,
                    "activity_frequency": profile.activity_frequency,
                    "last_activity": profile.last_activity,
                    "first_seen": profile.first_seen,
                    "preferred_tokens": profile.preferred_tokens,
                    "favorite_exchanges": profile.favorite_exchanges,
                    "favorite_dexes": profile.favorite_dexes,
                    "created_at": profile.created_at,
                    "updated_at": profile.updated_at,
                }
            )

        logger.info(f"Retrieved {len(data)} wallet profiles")
        return data

    except Exception as e:
        logger.error(f"Error fetching wallet profiles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wallet-profiles/{address}", response_model=Dict[str, Any])
async def get_wallet_profile_by_address(
    address: str,
    db: AsyncSession = Depends(get_db),
):
    """Get specific wallet profile by address."""
    try:
        query = select(WalletProfileORM).where(WalletProfileORM.address.ilike(address))
        result = await db.execute(query)
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(status_code=404, detail="Wallet profile not found")

        return {
            "wallet_id": str(profile.wallet_id),
            "address": profile.address,
            "blockchain": profile.blockchain,
            "entity_type": profile.entity_type,
            "entity_name": profile.entity_name,
            "total_trades": profile.total_trades,
            "profitable_trades": profile.profitable_trades,
            "win_rate": profile.win_rate,
            "avg_return_24h": profile.avg_return_24h,
            "avg_return_7d": profile.avg_return_7d,
            "best_trade_return": profile.best_trade_return,
            "worst_trade_return": profile.worst_trade_return,
            "behavior_cluster": profile.behavior_cluster,
            "tier": profile.tier,
            "confidence_score": profile.confidence_score,
            "activity_frequency": profile.activity_frequency,
            "last_activity": profile.last_activity,
            "first_seen": profile.first_seen,
            "preferred_tokens": profile.preferred_tokens,
            "favorite_exchanges": profile.favorite_exchanges,
            "favorite_dexes": profile.favorite_dexes,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }

    except Exception as e:
        logger.error(f"Error fetching wallet profile {address}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENTITIES ENDPOINTS
# ============================================================================


@router.get("/entities", response_model=List[Dict[str, Any]])
async def get_entities(
    limit: int = Query(100, ge=1, le=1000),
    verified_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all entities (organizations, exchanges, funds, etc.).

    Returns:
    - Entity ID, name, type
    - Associated wallets
    - Aggregated metrics
    - Verification status
    """
    try:
        query = select(EntityORM)

        if verified_only:
            query = query.where(EntityORM.verified == True)

        query = query.order_by(desc(EntityORM.updated_at)).limit(limit)

        result = await db.execute(query)
        entities = result.scalars().all()

        data = []
        for entity in entities:
            data.append(
                {
                    "entity_id": entity.entity_id,
                    "name": entity.name,
                    "entity_type": entity.entity_type,
                    "wallets": entity.wallets,
                    "description": entity.description,
                    "website": entity.website,
                    "twitter_handle": entity.twitter_handle,
                    "verified": entity.verified,
                    "verification_sources": entity.verification_sources,
                    "total_capital_tracked_usd": entity.total_capital_tracked_usd,
                    "total_transactions": entity.total_transactions,
                    "reliability_score": entity.reliability_score,
                    "created_at": entity.created_at,
                    "updated_at": entity.updated_at,
                }
            )

        logger.info(f"Retrieved {len(data)} entities")
        return data

    except Exception as e:
        logger.error(f"Error fetching entities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TRADE RECORDS ENDPOINTS
# ============================================================================


@router.get("/trade-records", response_model=List[Dict[str, Any]])
async def get_trade_records(
    wallet_address: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    profitable_only: bool = Query(False),
    unresolved_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """
    Get historical trade records.

    Returns trade-by-trade data:
    - Wallet address involved
    - Token in/out, amount, USD value
    - Exchange/DEX used
    - Profitability & return %
    - Timestamp
    """
    try:
        query = select(TradeRecordORM)

        if wallet_address:
            query = query.where(TradeRecordORM.wallet_address.ilike(wallet_address))

        if profitable_only:
            query = query.where(TradeRecordORM.is_profitable == True)

        if unresolved_only:
            query = query.where(TradeRecordORM.is_profitable.is_(None))

        query = query.order_by(desc(TradeRecordORM.timestamp)).limit(limit)

        result = await db.execute(query)
        trades = result.scalars().all()

        data = []
        for trade in trades:
            data.append(
                {
                    "trade_id": trade.trade_id,
                    "wallet_address": trade.wallet_address,
                    "token_in": trade.token_in,
                    "token_out": trade.token_out,
                    "amount_in": trade.amount_in,
                    "amount_out": trade.amount_out,
                    "usd_value": trade.usd_value,
                    "exchange_or_dex": trade.exchange_or_dex,
                    "is_profitable": trade.is_profitable,
                    "resolution_status": (
                        "pending"
                        if trade.is_profitable is None
                        else "profitable" if trade.is_profitable else "unprofitable"
                    ),
                    "return_percentage": trade.return_percentage,
                    "return_usd": trade.return_usd,
                    "timestamp": trade.timestamp,
                    "created_at": trade.created_at,
                }
            )

        logger.info(f"Retrieved {len(data)} trade records")
        return data

    except Exception as e:
        logger.error(f"Error fetching trade records: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trade-records/resolution-stats", response_model=Dict[str, Any])
async def get_trade_resolution_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get resolver coverage and unresolved backlog for trade outcomes."""
    try:
        snapshot = await db.run_sync(get_trade_resolution_snapshot)
        snapshot["timestamp"] = datetime.utcnow()
        return snapshot
    except Exception as e:
        logger.error(f"Error fetching trade resolution stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/trigger-resolver", response_model=Dict[str, Any])
async def trigger_resolver_manually(
    batch_size: int = Query(500, ge=1, le=5000),
):
    """Manually trigger the trade outcome resolver (debug/admin use)."""
    try:
        resolved_count = await run_in_threadpool(
            run_trade_outcome_resolution, batch_size
        )
        return {
            "status": "triggered",
            "resolved_count": resolved_count,
            "batch_size": batch_size,
            "timestamp": datetime.utcnow(),
        }
    except Exception as e:
        logger.error(f"Error triggering resolver manually: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENTITY PROFILES ENDPOINTS
# ============================================================================


@router.get("/entity-profiles", response_model=List[Dict[str, Any]])
async def get_entity_profiles(
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated entity profiles across all wallets.

    Returns:
    - Entity aggregate metrics
    - Number of wallets tracked
    - Combined performance stats
    - Risk scores
    """
    try:
        query = (
            select(EntityProfileORM)
            .order_by(desc(EntityProfileORM.updated_at))
            .limit(limit)
        )

        result = await db.execute(query)
        profiles = result.scalars().all()

        data = []
        for profile in profiles:
            data.append(
                {
                    "entity_id": profile.entity_id,
                    "entity_name": profile.entity_name,
                    "entity_type": profile.entity_type,
                    "total_wallets": profile.total_wallets,
                    "unique_tokens_traded": profile.unique_tokens_traded,
                    "total_trades_across_wallets": profile.total_trades_across_wallets,
                    "aggregate_win_rate": profile.aggregate_win_rate,
                    "aggregate_profitable_trades": profile.aggregate_profitable_trades,
                    "best_wallet": profile.best_wallet,
                    "best_wallet_win_rate": profile.best_wallet_win_rate,
                    "risk_score": profile.risk_score,
                    "prediction_confidence": profile.prediction_confidence,
                    "performance_last_7d": profile.performance_last_7d,
                    "performance_last_30d": profile.performance_last_30d,
                    "created_at": profile.created_at,
                    "updated_at": profile.updated_at,
                }
            )

        logger.info(f"Retrieved {len(data)} entity profiles")
        return data

    except Exception as e:
        logger.error(f"Error fetching entity profiles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PROCESSED EVENTS WITH AGENT B DATA ENDPOINTS
# ============================================================================


@router.get("/processed-events", response_model=List[Dict[str, Any]])
async def get_processed_events_with_agent_b(
    limit: int = Query(100, ge=1, le=1000),
    priority: Optional[str] = Query(
        None, description="Filter by priority: HIGH, MEDIUM, LOW"
    ),
    user_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get ProcessedEvents with embedded Agent B profiling data.

    Returns:
    - Event ID, timestamp, priority
    - Complete event_data JSON (includes agent_b profiling)
    - User ID associated
    - Processing metadata
    """
    try:
        query = select(ProcessedEvent)

        if priority:
            query = query.where(ProcessedEvent.priority == priority)

        if user_id:
            query = query.where(ProcessedEvent.user_id == user_id)

        query = query.order_by(desc(ProcessedEvent.timestamp)).limit(limit)

        result = await db.execute(query)
        events = result.scalars().all()

        data = []
        for event in events:
            event_dict = {
                "id": event.id,
                "user_id": event.user_id,
                "timestamp": event.timestamp,
                "priority": event.priority,
                "score": event.score,
                "multi_source": event.multi_source,
                "engagement": event.engagement,
                "bot": event.bot,
                "dedup": event.dedup,
                "event_data": event.event_data,  # Full JSON with agent_b
                "updated_at": event.updated_at,
            }
            data.append(event_dict)

        logger.info(f"Retrieved {len(data)} processed events with Agent B data")
        return data

    except Exception as e:
        logger.error(f"Error fetching processed events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/processed-events/{event_id}", response_model=Dict[str, Any])
async def get_processed_event_by_id(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get specific ProcessedEvent with full Agent B profiling."""
    try:
        query = select(ProcessedEvent).where(ProcessedEvent.id == event_id)
        result = await db.execute(query)
        event = result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        return {
            "id": event.id,
            "user_id": event.user_id,
            "timestamp": event.timestamp,
            "priority": event.priority,
            "score": event.score,
            "multi_source": event.multi_source,
            "engagement": event.engagement,
            "bot": event.bot,
            "dedup": event.dedup,
            "event_data": event.event_data,  # Full JSON with agent_b
            "updated_at": event.updated_at,
        }

    except Exception as e:
        logger.error(f"Error fetching event {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATISTICS & SUMMARY ENDPOINTS
# ============================================================================


@router.get("/statistics/summary", response_model=Dict[str, Any])
async def get_agent_b_statistics(
    db: AsyncSession = Depends(get_db),
):
    """
    Get high-level statistics on Agent B data in database.

    Returns counts and summaries of:
    - Total wallet profiles
    - Total entities
    - Total trade records
    - Average metrics
    """
    try:
        # Count wallet profiles
        wallet_count = (
            await db.execute(select(func.count(WalletProfileORM.wallet_id)))
        ).scalar() or 0

        # Count entities
        entity_count = (
            await db.execute(select(func.count(EntityORM.entity_id)))
        ).scalar() or 0

        # Count trade records
        trade_count = (
            await db.execute(select(func.count(TradeRecordORM.trade_id)))
        ).scalar() or 0

        # Count entity profiles
        profile_count = (
            await db.execute(select(func.count(EntityProfileORM.entity_id)))
        ).scalar() or 0

        # Count processed events with agent_b
        events_with_agent_b = (
            await db.execute(select(func.count(ProcessedEvent.id)))
        ).scalar() or 0

        # Diagnose trade-record pipeline capture coverage.
        # NOTE: The live on-chain collector mainly emits transfer events; only
        # swap-shaped payloads are eligible for trade record persistence.
        event_payloads = (
            await db.execute(select(ProcessedEvent.event_data))
        ).scalars().all()

        trade_ids = (
            await db.execute(select(TradeRecordORM.trade_id))
        ).scalars().all()

        onchain_transfer_events = 0
        onchain_swap_events = 0
        trade_eligible_events = 0
        payload_parse_failures = 0

        # Distinguish legacy/manual UUID-like IDs from current deterministic IDs.
        # Current deterministic format is usually: "<tx_hash>_<log_index>_<wallet>"
        # or a compact 40-char hash fallback (no dashes).
        legacy_trade_id_count = 0
        deterministic_trade_id_count = 0

        for trade_id in trade_ids:
            if not isinstance(trade_id, str):
                continue
            normalized = trade_id.strip()
            if not normalized:
                continue

            if "_" in normalized or (len(normalized) == 40 and "-" not in normalized):
                deterministic_trade_id_count += 1
            else:
                # UUID-like or any other legacy format.
                legacy_trade_id_count += 1

        for payload in event_payloads:
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload_parse_failures += 1
                    continue

            if not isinstance(payload, dict):
                continue

            source = str(payload.get("source", "")).lower()
            content = payload.get("content", {})
            if not isinstance(content, dict):
                content = {}

            event_type = str(content.get("event_type", "")).lower()
            tx_type = str(content.get("transaction_type", "")).lower()

            if source == "ethereum" and tx_type == "transfer":
                onchain_transfer_events += 1
            if source == "ethereum" and (event_type == "dex_swap" or tx_type == "swap"):
                onchain_swap_events += 1

            if extract_trade_record_payload(payload) is not None:
                trade_eligible_events += 1

        trade_record_capture_rate = (
            round((trade_count / trade_eligible_events), 4)
            if trade_eligible_events > 0
            else 0.0
        )

        # Average win rate
        avg_win_rate = (
            await db.execute(select(func.avg(WalletProfileORM.win_rate)))
        ).scalar() or 0

        # Average confidence score
        avg_confidence = (
            await db.execute(select(func.avg(WalletProfileORM.confidence_score)))
        ).scalar() or 0

        return {
            "total_wallet_profiles": wallet_count,
            "total_entities": entity_count,
            "total_trade_records": trade_count,
            "deterministic_trade_records": deterministic_trade_id_count,
            "legacy_or_manual_trade_records": legacy_trade_id_count,
            "total_entity_profiles": profile_count,
            "total_processed_events": events_with_agent_b,
            "onchain_transfer_events": onchain_transfer_events,
            "onchain_swap_events": onchain_swap_events,
            "trade_eligible_events": trade_eligible_events,
            "trade_record_capture_rate": trade_record_capture_rate,
            "event_payload_parse_failures": payload_parse_failures,
            "average_wallet_win_rate": round(avg_win_rate, 4),
            "average_confidence_score": round(avg_confidence, 4),
            "timestamp": datetime.utcnow(),
        }

    except Exception as e:
        logger.error(f"Error fetching statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
