"""Trade record writer and resolver for Agent B intelligence.

This module adds two capabilities:
1) Deterministic, idempotent trade-record persistence from normalized events.
2) Deferred profitability resolution once a matching exit trade is observed.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.config.db import SessionLocal
from app.modules.intelligence.infrastructure.models import TradeRecordORM

logger = logging.getLogger("trade-records")
EPSILON = 1e-12


def _parse_timestamp(raw_timestamp: Any) -> datetime:
    """Parse event timestamp with robust fallback to UTC now."""
    if isinstance(raw_timestamp, datetime):
        return raw_timestamp.replace(tzinfo=None)

    if isinstance(raw_timestamp, str) and raw_timestamp.strip():
        text = raw_timestamp.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text).replace(tzinfo=None)
        except Exception:
            pass

    return datetime.utcnow()


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def is_trade_like_event(event: Dict[str, Any]) -> bool:
    """Return True when event payload looks like a DEX swap/trade."""
    if not isinstance(event, dict):
        return False

    source = str(event.get("source", "")).lower()
    if source and source != "ethereum":
        return False

    content = event.get("content", {})
    if not isinstance(content, dict):
        return False

    event_type = str(content.get("event_type", "")).lower()
    tx_type = str(content.get("transaction_type", "")).lower()

    has_swap_shape = (
        content.get("token_in") is not None
        and content.get("token_out") is not None
        and content.get("amount_in") is not None
        and content.get("amount_out") is not None
    )

    return event_type in ("dex_swap", "swap") or tx_type == "swap" or has_swap_shape


def extract_trade_record_payload(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract normalized trade payload from an event; return None if insufficient."""
    if not is_trade_like_event(event):
        logger.debug(
            "[TRADE] Skipped: non trade-like event | event_id=%s",
            event.get("id") if isinstance(event, dict) else None,
        )
        return None

    content = event.get("content", {}) if isinstance(event.get("content"), dict) else {}

    wallet_address = (
        content.get("wallet_address")
        or content.get("trader_address")
        or content.get("from_address")
        or event.get("wallet_address")
        or event.get("address")
    )
    if not isinstance(wallet_address, str) or not wallet_address.strip():
        logger.debug(
            "[TRADE] Skipped: missing wallet address | event_id=%s tx=%s",
            event.get("id"),
            content.get("transaction_hash"),
        )
        return None

    token_in = content.get("token_in") or content.get("token")
    token_out = content.get("token_out")

    amount_in = _to_float(content.get("amount_in"), 0.0)
    amount_out = _to_float(content.get("amount_out"), 0.0)
    usd_value = _to_float(content.get("usd_value"), 0.0)
    has_swap_shape = amount_in > 0 and amount_out > 0

    if not token_in or not token_out:
        logger.debug(
            "[TRADE] Skipped: missing token fields | event_id=%s tx=%s token_in=%s token_out=%s",
            event.get("id"),
            content.get("transaction_hash"),
            token_in,
            token_out,
        )
        return None

    if not has_swap_shape:
        logger.debug(
            "[TRADE] Skipped: invalid swap amounts | event_id=%s tx=%s amount_in=%s amount_out=%s usd_value=%s",
            event.get("id"),
            content.get("transaction_hash"),
            amount_in,
            amount_out,
            usd_value,
        )
        return None

    if usd_value < 0:
        logger.debug(
            "[TRADE] Skipped: negative usd_value | event_id=%s tx=%s usd_value=%s",
            event.get("id"),
            content.get("transaction_hash"),
            usd_value,
        )
        return None

    timestamp = _parse_timestamp(event.get("timestamp") or content.get("timestamp"))

    return {
        "event_id": str(event.get("id", "")),
        "transaction_hash": str(content.get("transaction_hash") or ""),
        "log_index": (
            content.get("log_index")
            or content.get("event_index")
            or content.get("transaction_index")
            or 0
        ),
        "wallet_address": wallet_address.lower(),
        "token_in": str(token_in),
        "token_out": str(token_out),
        "amount_in": amount_in,
        "amount_out": amount_out,
        "usd_value": usd_value,
        "exchange_or_dex": str(
            content.get("dex") or content.get("exchange_detected") or "unknown"
        ),
        "timestamp": timestamp,
    }


def build_deterministic_trade_id(payload: Dict[str, Any]) -> str:
    """Build deterministic trade_id using on-chain identities first."""
    tx_hash = str(
        payload.get("transaction_hash") or payload.get("tx_hash") or ""
    ).strip()
    wallet = str(payload.get("wallet_address") or "").strip().lower()
    log_index = payload.get("log_index")
    log_index = str(log_index if log_index is not None else 0).strip()

    # Primary identity path: immutable chain identifiers.
    if tx_hash:
        return f"{tx_hash}_{log_index}_{wallet}"[:120]

    # Fallback identity path (non-chain payloads): compact normalized hash.
    base = "|".join(
        [
            wallet,
            str(payload.get("token_in") or ""),
            str(payload.get("token_out") or ""),
            f"{_to_float(payload.get('amount_in')):.12f}",
            payload.get("timestamp").isoformat() if payload.get("timestamp") else "",
        ]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:40]


def upsert_trade_record_from_event(db, event: Dict[str, Any]) -> str:
    """Persist trade record from event idempotently.

    Returns one of: created, updated, skipped
    """
    content = event.get("content", {}) if isinstance(event.get("content"), dict) else {}
    event_type = str(content.get("event_type", "")).lower()
    tx_type = str(content.get("transaction_type", "")).lower()
    tx_hash = str(content.get("transaction_hash") or "")
    usd_value = _to_float(content.get("usd_value"), 0.0)

    if event_type in ("dex_swap", "swap") or tx_type == "swap":
        logger.debug(
            "[TRADE] Processing swap tx=%s usd=%s event_id=%s",
            tx_hash,
            usd_value,
            event.get("id"),
        )

    payload = extract_trade_record_payload(event)
    if payload is None:
        logger.debug(
            "[TRADE] Upsert skipped after extraction | event_id=%s tx=%s",
            event.get("id"),
            tx_hash,
        )
        return "skipped"

    trade_id = build_deterministic_trade_id(payload)
    existing = (
        db.query(TradeRecordORM).filter(TradeRecordORM.trade_id == trade_id).first()
    )

    if existing:
        # Keep deterministic identity; refresh mutable fields if needed.
        existing.usd_value = payload["usd_value"]
        existing.exchange_or_dex = payload["exchange_or_dex"]
        existing.timestamp = payload["timestamp"]
        db.add(existing)
        return "updated"

    trade = TradeRecordORM(
        trade_id=trade_id,
        wallet_address=payload["wallet_address"],
        token_in=payload["token_in"],
        token_out=payload["token_out"],
        amount_in=payload["amount_in"],
        amount_out=payload["amount_out"],
        usd_value=payload["usd_value"],
        exchange_or_dex=payload["exchange_or_dex"],
        timestamp=payload["timestamp"],
    )
    db.add(trade)
    return "created"


def resolve_pending_trade_outcomes(db, batch_size: int = 200) -> int:
    """Resolve trade outcomes using deterministic FIFO position accounting.

    Prevents double-counting by recomputing realized PnL from chronological wallet
    history and consuming lots exactly once per sell leg.
    """
    unresolved_candidates = (
        db.query(TradeRecordORM.wallet_address)
        .filter(TradeRecordORM.is_profitable.is_(None))
        .order_by(TradeRecordORM.timestamp.asc())
        .limit(batch_size)
        .all()
    )
    wallet_addresses = [row[0] for row in unresolved_candidates if row and row[0]]
    if not wallet_addresses:
        return 0

    # De-duplicate while preserving order.
    seen = set()
    ordered_wallets = []
    for address in wallet_addresses:
        if address in seen:
            continue
        seen.add(address)
        ordered_wallets.append(address)

    resolved_count = 0
    skipped_buy_lot_zero_usd = 0

    for wallet_address in ordered_wallets:
        trades = (
            db.query(TradeRecordORM)
            .filter(TradeRecordORM.wallet_address == wallet_address)
            .order_by(TradeRecordORM.timestamp.asc(), TradeRecordORM.trade_id.asc())
            .all()
        )
        if not trades:
            continue

        # Reset previously derived outcomes; recompute deterministically.
        for trade in trades:
            if (
                trade.is_profitable is not None
                or trade.return_usd is not None
                or trade.return_percentage is not None
            ):
                trade.is_profitable = None
                trade.return_usd = None
                trade.return_percentage = None
                db.add(trade)

        # token -> list of lots [{amount, unit_cost}]
        open_positions: Dict[str, list[Dict[str, float]]] = {}

        for trade in trades:
            token_in = (trade.token_in or "").strip()
            token_out = (trade.token_out or "").strip()
            amount_in = _to_float(trade.amount_in, 0.0)
            amount_out = _to_float(trade.amount_out, 0.0)
            trade_value_usd = _to_float(trade.usd_value, 0.0)

            # SELL LEG: token_in leaves wallet; realize PnL against FIFO lots.
            if token_in and amount_in > EPSILON and trade_value_usd > EPSILON:
                queue = open_positions.get(token_in, [])
                remaining_to_sell = amount_in
                total_cost_basis = 0.0

                while remaining_to_sell > EPSILON and queue:
                    lot = queue[0]
                    lot_amount = _to_float(lot.get("amount"), 0.0)
                    lot_unit_cost = _to_float(lot.get("unit_cost"), 0.0)
                    if lot_amount <= EPSILON:
                        queue.pop(0)
                        continue

                    sold_from_lot = min(remaining_to_sell, lot_amount)
                    total_cost_basis += sold_from_lot * lot_unit_cost

                    lot["amount"] = lot_amount - sold_from_lot
                    remaining_to_sell -= sold_from_lot

                    if lot["amount"] <= EPSILON:
                        queue.pop(0)

                # Persist queue updates.
                open_positions[token_in] = queue

                # Resolve only when sale amount is fully covered by open lots.
                if remaining_to_sell <= EPSILON and total_cost_basis > EPSILON:
                    realized_pnl = trade_value_usd - total_cost_basis
                    realized_pct = (realized_pnl / total_cost_basis) * 100.0
                    trade.is_profitable = realized_pnl > 0
                    trade.return_usd = realized_pnl
                    trade.return_percentage = realized_pct
                    db.add(trade)
                    resolved_count += 1

            # BUY LEG: token_out enters wallet; add a new lot.
            if token_out and amount_out > EPSILON and trade_value_usd > EPSILON:
                queue = open_positions.setdefault(token_out, [])
                queue.append(
                    {
                        "amount": amount_out,
                        "unit_cost": trade_value_usd / amount_out,
                    }
                )
            elif token_out and amount_out > EPSILON and trade_value_usd <= EPSILON:
                skipped_buy_lot_zero_usd += 1
                logger.debug(
                    "[TRADE-RESOLVER] Skipping buy lot — usd_value=0 (price oracle failed) | trade_id=%s",
                    trade.trade_id,
                )

    if skipped_buy_lot_zero_usd > 0:
        logger.info(
            "[TRADE-RESOLVER] Zero-USD buy legs skipped: %s",
            skipped_buy_lot_zero_usd,
        )

    return resolved_count


def run_trade_outcome_resolution(batch_size: int = 200) -> int:
    """Run resolver in its own DB session for scheduled execution."""
    db = SessionLocal()
    try:
        unresolved_before = (
            db.query(TradeRecordORM)
            .filter(TradeRecordORM.is_profitable.is_(None))
            .count()
        )

        resolved = resolve_pending_trade_outcomes(db, batch_size=batch_size)
        if resolved > 0:
            db.commit()
            unresolved_after = (
                db.query(TradeRecordORM)
                .filter(TradeRecordORM.is_profitable.is_(None))
                .count()
            )
            logger.info(
                "[TRADE-RESOLVER] Resolved outcomes for "
                f"{resolved} trades | unresolved: {unresolved_before} -> {unresolved_after}"
            )
        else:
            db.rollback()
        return resolved
    except Exception as e:
        db.rollback()
        logger.error(f"[TRADE-RESOLVER] Failed: {e}", exc_info=True)
        return 0
    finally:
        db.close()


def get_trade_resolution_snapshot(db) -> Dict[str, Any]:
    """Return compact resolver health stats for monitoring/debug endpoints."""
    total = db.query(TradeRecordORM).count()
    unresolved = (
        db.query(TradeRecordORM).filter(TradeRecordORM.is_profitable.is_(None)).count()
    )
    resolved_profitable = (
        db.query(TradeRecordORM).filter(TradeRecordORM.is_profitable.is_(True)).count()
    )
    resolved_unprofitable = (
        db.query(TradeRecordORM).filter(TradeRecordORM.is_profitable.is_(False)).count()
    )
    resolved_total = resolved_profitable + resolved_unprofitable

    oldest_unresolved = (
        db.query(TradeRecordORM)
        .filter(TradeRecordORM.is_profitable.is_(None))
        .order_by(TradeRecordORM.timestamp.asc())
        .first()
    )

    return {
        "total_trades": total,
        "resolved_trades": resolved_total,
        "unresolved_trades": unresolved,
        "resolved_profitable": resolved_profitable,
        "resolved_unprofitable": resolved_unprofitable,
        "resolution_coverage": round((resolved_total / total), 4) if total > 0 else 0.0,
        "oldest_unresolved_timestamp": (
            oldest_unresolved.timestamp.isoformat()
            if oldest_unresolved and oldest_unresolved.timestamp
            else None
        ),
    }
