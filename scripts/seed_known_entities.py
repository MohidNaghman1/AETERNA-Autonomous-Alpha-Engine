"""Seed Agent B known entities and wallet labels from CSV.

Usage:
    python scripts/seed_known_entities.py --csv data/known_entities.example.csv
    python scripts/seed_known_entities.py --csv labels.csv --dry-run
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

from app.config.db import SessionLocal
from app.modules.intelligence.domain.agent_b_models import (
    BehaviorCluster,
    EntityType,
    WalletTier,
)
from app.modules.intelligence.infrastructure.models import EntityORM, WalletProfileORM

ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
DEFAULT_RELIABILITY = 0.85


@dataclass
class SeedEntity:
    entity_id: str
    name: str
    entity_type: str
    wallets: set[str] = field(default_factory=set)
    description: str | None = None
    website: str | None = None
    twitter_handle: str | None = None
    verified: bool = True
    verification_sources: set[str] = field(default_factory=set)
    total_capital_tracked_usd: float = 0.0
    total_transactions: int = 0
    reliability_score: float = DEFAULT_RELIABILITY


def _clean(value: object) -> str:
    return str(value or "").strip()


def _bool(value: object, default: bool = True) -> bool:
    text = _clean(value).lower()
    if not text:
        return default
    return text in {"1", "true", "yes", "y", "verified"}


def _float(value: object, default: float = 0.0) -> float:
    text = _clean(value).replace(",", "")
    if not text:
        return default
    return float(text)


def _int(value: object, default: int = 0) -> int:
    text = _clean(value).replace(",", "")
    if not text:
        return default
    return int(float(text))


def _sources(raw: object) -> set[str]:
    return {item.strip() for item in _clean(raw).split(";") if item.strip()}


def normalize_entity_type(raw: object) -> str:
    entity_type = _clean(raw).lower()
    if not entity_type:
        return EntityType.UNKNOWN.value

    aliases = {
        "exchange_hot_wallet": EntityType.EXCHANGE.value,
        "exchange_deposit": EntityType.EXCHANGE.value,
        "cex": EntityType.EXCHANGE.value,
        "fund": EntityType.VC_FUND.value,
        "vc": EntityType.VC_FUND.value,
        "market-maker": EntityType.MARKET_MAKER.value,
        "market maker": EntityType.MARKET_MAKER.value,
        "bot": EntityType.TRADING_BOT.value,
    }
    entity_type = aliases.get(entity_type, entity_type)
    allowed = {item.value for item in EntityType}
    if entity_type not in allowed:
        raise ValueError(
            f"Unsupported entity_type '{raw}'. Use one of: {', '.join(sorted(allowed))}"
        )
    return entity_type


def normalize_wallet(raw: object) -> str:
    wallet = _clean(raw).lower()
    if not ADDRESS_RE.match(wallet):
        raise ValueError(f"Invalid Ethereum address: {raw}")
    return wallet


def load_seed_entities(csv_path: Path) -> dict[str, SeedEntity]:
    entities: dict[str, SeedEntity] = {}

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"entity_id", "name", "entity_type", "wallet_address"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required CSV columns: {', '.join(sorted(missing))}")

        for row_number, row in enumerate(reader, start=2):
            entity_id = _clean(row.get("entity_id"))
            if not entity_id:
                raise ValueError(f"Row {row_number}: entity_id is required")

            entity_type = normalize_entity_type(row.get("entity_type"))
            wallet = normalize_wallet(row.get("wallet_address"))
            entity = entities.get(entity_id)
            if not entity:
                entity = SeedEntity(
                    entity_id=entity_id,
                    name=_clean(row.get("name")),
                    entity_type=entity_type,
                    description=_clean(row.get("description")) or None,
                    website=_clean(row.get("website")) or None,
                    twitter_handle=_clean(row.get("twitter_handle")) or None,
                    verified=_bool(row.get("verified"), default=True),
                    verification_sources=_sources(row.get("verification_sources")),
                    total_capital_tracked_usd=_float(
                        row.get("total_capital_tracked_usd")
                    ),
                    total_transactions=_int(row.get("total_transactions")),
                    reliability_score=_float(
                        row.get("reliability_score"), default=DEFAULT_RELIABILITY
                    ),
                )
                entities[entity_id] = entity
            elif entity.entity_type != entity_type:
                raise ValueError(
                    f"Row {row_number}: entity_id {entity_id} mixes entity types "
                    f"({entity.entity_type} vs {entity_type})"
                )

            entity.wallets.add(wallet)
            entity.verification_sources.update(_sources(row.get("verification_sources")))

    return entities


def _profile_confidence(entity: SeedEntity) -> float:
    base = (
        entity.reliability_score
        if entity.reliability_score is not None
        else DEFAULT_RELIABILITY
    )
    if entity.verified:
        base = max(base, 0.8)
    return min(max(base, 0.0), 1.0)


def upsert_entities(entities: Iterable[SeedEntity], dry_run: bool = False) -> dict:
    entities = list(entities)
    stats = {"entities_created": 0, "entities_updated": 0, "wallet_profiles_upserted": 0}
    now = datetime.utcnow()

    if dry_run:
        wallet_count = sum(len(entity.wallets) for entity in entities)
        return {
            **stats,
            "dry_run": True,
            "entities_seen": len(entities),
            "wallets_seen": wallet_count,
        }

    db = SessionLocal()
    try:
        for entity in entities:
            existing = db.query(EntityORM).filter(EntityORM.entity_id == entity.entity_id).first()
            wallets = sorted(entity.wallets)
            sources = sorted(entity.verification_sources)

            if existing:
                existing_wallets = set(existing.wallets or [])
                existing.wallets = sorted(existing_wallets | set(wallets))
                existing.name = entity.name or existing.name
                existing.entity_type = entity.entity_type
                existing.description = entity.description or existing.description
                existing.website = entity.website or existing.website
                existing.twitter_handle = entity.twitter_handle or existing.twitter_handle
                existing.verified = entity.verified
                existing.verification_sources = sorted(
                    set(existing.verification_sources or []) | set(sources)
                )
                existing.total_capital_tracked_usd = max(
                    existing.total_capital_tracked_usd or 0.0,
                    entity.total_capital_tracked_usd,
                )
                existing.total_transactions = max(
                    existing.total_transactions or 0,
                    entity.total_transactions,
                )
                existing.reliability_score = max(
                    existing.reliability_score or 0.0,
                    entity.reliability_score,
                )
                existing.updated_at = now
                stats["entities_updated"] += 1
            else:
                db.add(
                    EntityORM(
                        entity_id=entity.entity_id,
                        name=entity.name,
                        entity_type=entity.entity_type,
                        wallets=wallets,
                        description=entity.description,
                        website=entity.website,
                        twitter_handle=entity.twitter_handle,
                        verified=entity.verified,
                        verification_sources=sources,
                        total_capital_tracked_usd=entity.total_capital_tracked_usd,
                        total_transactions=entity.total_transactions,
                        reliability_score=entity.reliability_score,
                        created_at=now,
                        updated_at=now,
                    )
                )
                stats["entities_created"] += 1

            confidence = _profile_confidence(entity)
            for wallet in wallets:
                profile = (
                    db.query(WalletProfileORM)
                    .filter(WalletProfileORM.address == wallet)
                    .first()
                )
                if not profile:
                    profile = WalletProfileORM(
                        address=wallet,
                        blockchain="ethereum",
                        total_trades=0,
                        profitable_trades=0,
                        win_rate=0.0,
                        avg_return_24h=0.0,
                        avg_return_7d=0.0,
                        best_trade_return=0.0,
                        worst_trade_return=0.0,
                        behavior_cluster=BehaviorCluster.UNKNOWN.value,
                        tier=WalletTier.UNVERIFIED.value,
                        activity_frequency="inactive",
                        first_seen=now,
                        last_activity=now,
                        preferred_tokens=[],
                        favorite_exchanges=[],
                        favorite_dexes=[],
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(profile)

                profile.entity_type = entity.entity_type
                profile.entity_name = entity.name
                profile.confidence_score = max(profile.confidence_score or 0.0, confidence)
                profile.updated_at = now
                stats["wallet_profiles_upserted"] += 1

        db.commit()
        return stats
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Agent B known wallet labels")
    parser.add_argument("--csv", required=True, type=Path, help="CSV file to import")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing")
    args = parser.parse_args()

    entities_by_id = load_seed_entities(args.csv)
    stats = upsert_entities(list(entities_by_id.values()), dry_run=args.dry_run)
    print(
        "Seed complete: "
        f"{stats.get('entities_created', 0)} created, "
        f"{stats.get('entities_updated', 0)} updated, "
        f"{stats.get('wallet_profiles_upserted', 0)} wallet profiles upserted"
        + (" (dry run)" if args.dry_run else "")
    )


if __name__ == "__main__":
    main()
