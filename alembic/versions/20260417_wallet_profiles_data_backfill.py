"""Backfill wallet_profiles enum casing and cold-start defaults.

Revision ID: wp_backfill_20260417
Revises: add_processed_event_updated_at
Create Date: 2026-04-17 18:40:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "wp_backfill_20260417"
down_revision = "add_processed_event_updated_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Normalize enum-like strings (supports legacy forms like "BehaviorCluster.UNKNOWN")
    op.execute("""
        UPDATE wallet_profiles
        SET behavior_cluster = lower(
            btrim(
                CASE
                    WHEN behavior_cluster IS NULL THEN 'unknown'
                    WHEN position('.' in behavior_cluster) > 0
                        THEN split_part(behavior_cluster, '.', 2)
                    ELSE behavior_cluster
                END
            )
        )
        WHERE behavior_cluster IS NULL
           OR behavior_cluster <> lower(
                btrim(
                    CASE
                        WHEN position('.' in behavior_cluster) > 0
                            THEN split_part(behavior_cluster, '.', 2)
                        ELSE behavior_cluster
                    END
                )
            );
        """)

    op.execute("""
        UPDATE wallet_profiles
        SET tier = lower(
            btrim(
                CASE
                    WHEN tier IS NULL THEN 'unverified'
                    WHEN position('.' in tier) > 0
                        THEN split_part(tier, '.', 2)
                    ELSE tier
                END
            )
        )
        WHERE tier IS NULL
           OR tier <> lower(
                btrim(
                    CASE
                        WHEN position('.' in tier) > 0
                            THEN split_part(tier, '.', 2)
                        ELSE tier
                    END
                )
            );
        """)

    # 2) Enforce known canonical values for enums used by Agent B model parsing.
    op.execute("""
        UPDATE wallet_profiles
        SET behavior_cluster = 'unknown'
        WHERE behavior_cluster IS NULL
           OR behavior_cluster = ''
           OR behavior_cluster NOT IN (
               'accumulator',
               'trader',
               'liquidator',
               'arbitrageur',
               'whale',
               'bot',
               'unknown'
           );
        """)

    op.execute("""
        UPDATE wallet_profiles
        SET tier = 'unverified'
        WHERE tier IS NULL
           OR tier = ''
           OR tier NOT IN (
               'high_performer',
               'medium_performer',
               'low_performer',
               'unverified'
           );
        """)

    # 3) Backfill first_seen when missing so cold-start wallets are still timestamped.
    op.execute("""
        UPDATE wallet_profiles
        SET first_seen = COALESCE(first_seen, created_at, updated_at, NOW())
        WHERE first_seen IS NULL;
        """)

    # 4) Prevent cold-start unknown/unverified wallets from carrying zero confidence.
    op.execute("""
        UPDATE wallet_profiles
        SET confidence_score = 0.1
        WHERE COALESCE(confidence_score, 0) <= 0
          AND lower(COALESCE(entity_type, 'unknown')) = 'unknown'
          AND lower(COALESCE(tier, 'unverified')) = 'unverified';
        """)


def downgrade() -> None:
    # Irreversible data normalization/backfill.
    pass
