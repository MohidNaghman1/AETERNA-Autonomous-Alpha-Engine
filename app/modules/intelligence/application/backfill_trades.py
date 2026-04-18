"""Backfill TradeRecord rows from historical processed events.

This utility reuses the exact same extraction/upsert logic as the live pipeline
so historical and real-time behavior remain consistent.
"""

from __future__ import annotations

import argparse
import logging
from typing import Any, Dict

from app.config.db import SessionLocal
from app.modules.intelligence.application.trade_records import upsert_trade_record_from_event
from app.modules.intelligence.infrastructure.models import ProcessedEvent

logger = logging.getLogger("trade-backfill")


def _to_event_dict(processed: ProcessedEvent) -> Dict[str, Any]:
    event_data = processed.event_data if isinstance(processed.event_data, dict) else {}
    content = event_data.get("content", {}) if isinstance(event_data.get("content"), dict) else {}
    source = event_data.get("source") or "ethereum"

    return {
        "id": str(processed.id),
        "source": source,
        "timestamp": processed.timestamp,
        "content": content,
    }


def run_backfill(limit: int = 10000, commit_every: int = 500) -> Dict[str, int]:
    db = SessionLocal()
    created = 0
    updated = 0
    skipped = 0
    failed = 0

    try:
        rows = (
            db.query(ProcessedEvent)
            .order_by(ProcessedEvent.timestamp.asc())
            .limit(limit)
            .all()
        )

        for idx, processed in enumerate(rows, start=1):
            try:
                event_dict = _to_event_dict(processed)
                # Guard: process only ethereum-origin events for trade extraction.
                if str(event_dict.get("source", "")).lower() != "ethereum":
                    skipped += 1
                    continue

                result = upsert_trade_record_from_event(db, event_dict)
                if result == "created":
                    created += 1
                elif result == "updated":
                    updated += 1
                else:
                    skipped += 1

                if idx % commit_every == 0:
                    db.commit()
            except Exception as e:
                logger.error(f"Backfill failure for ProcessedEvent {processed.id}: {e}")
                failed += 1

        db.commit()
        return {
            "scanned": len(rows),
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill TradeRecord rows")
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--commit-every", type=int, default=500)
    args = parser.parse_args()

    summary = run_backfill(limit=max(1, args.limit), commit_every=max(1, args.commit_every))
    print("[BACKFILL COMPLETE]", summary)


if __name__ == "__main__":
    main()
