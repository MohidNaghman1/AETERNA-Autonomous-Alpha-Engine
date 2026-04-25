"""Trade resolver backlog report.

Prints unresolved trade-record backlog grouped by wallet address, with oldest
pending timestamp to help prioritize resolver improvements.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime

from sqlalchemy import case, func

from app.config.db import SessionLocal
from app.modules.intelligence.infrastructure.models import TradeRecordORM


def _iso_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def build_backlog_report(limit: int = 20) -> dict:
    db = SessionLocal()
    try:
        total_unresolved = (
            db.query(TradeRecordORM)
            .filter(TradeRecordORM.is_profitable.is_(None))
            .count()
        )

        total_trades = db.query(TradeRecordORM).count()

        top_wallets = (
            db.query(
                TradeRecordORM.wallet_address.label("wallet_address"),
                func.count(TradeRecordORM.trade_id).label("unresolved_count"),
                func.min(TradeRecordORM.timestamp).label("oldest_unresolved"),
                func.max(TradeRecordORM.timestamp).label("latest_unresolved"),
            )
            .filter(TradeRecordORM.is_profitable.is_(None))
            .group_by(TradeRecordORM.wallet_address)
            .order_by(func.count(TradeRecordORM.trade_id).desc())
            .limit(limit)
            .all()
        )
        token_pairs = (
            db.query(
                TradeRecordORM.token_in.label("token_in"),
                TradeRecordORM.token_out.label("token_out"),
                func.count(TradeRecordORM.trade_id).label("total"),
                func.sum(
                    case((TradeRecordORM.is_profitable.is_(None), 1), else_=0)
                ).label("unresolved"),
                func.avg(TradeRecordORM.usd_value).label("avg_usd"),
            )
            .group_by(TradeRecordORM.token_in, TradeRecordORM.token_out)
            .order_by(func.count(TradeRecordORM.trade_id).desc())
            .limit(20)
            .all()
        )

        rows = [
            {
                "wallet_address": row.wallet_address,
                "unresolved_count": int(row.unresolved_count or 0),
                "oldest_unresolved": _iso_or_none(row.oldest_unresolved),
                "latest_unresolved": _iso_or_none(row.latest_unresolved),
            }
            for row in top_wallets
        ]

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "total_trades": int(total_trades or 0),
            "total_unresolved": int(total_unresolved or 0),
            "unresolved_coverage": (
                round((total_unresolved / total_trades), 4) if total_trades else 0.0
            ),
            "wallets": rows,
            "token_pairs": [
                {
                    "token_in": row.token_in,
                    "token_out": row.token_out,
                    "total": int(row.total or 0),
                    "unresolved": int(row.unresolved or 0),
                    "avg_usd": round(float(row.avg_usd or 0), 4),
                }
                for row in token_pairs
            ],
        }
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report unresolved trade backlog grouped by wallet"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="How many wallets to include (default: 20)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output instead of table-style lines",
    )
    args = parser.parse_args()

    report = build_backlog_report(limit=max(1, args.limit))

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print("=" * 72)
    print("Trade Resolver Backlog Report")
    print("=" * 72)
    print(f"Generated at       : {report['generated_at']}")
    print(f"Total trades       : {report['total_trades']}")
    print(f"Total unresolved   : {report['total_unresolved']}")
    print(f"Unresolved coverage: {report['unresolved_coverage']:.2%}")
    print("-" * 72)

    if not report["wallets"]:
        print("No unresolved trade records found. ✅")
        return

    for idx, row in enumerate(report["wallets"], start=1):
        print(
            f"{idx:>2}. {row['wallet_address']} | "
            f"pending={row['unresolved_count']} | "
            f"oldest={row['oldest_unresolved']} | "
            f"latest={row['latest_unresolved']}"
        )

    print("-" * 72)
    print("Top Token Pairs (by trade count):")
    for row in report.get("token_pairs", []):
        print(
            f"  {row['token_in']:<12} -> {row['token_out']:<12} | "
            f"total={row['total']} unresolved={row['unresolved']} avg_usd=${row['avg_usd']}"
        )


if __name__ == "__main__":
    main()
