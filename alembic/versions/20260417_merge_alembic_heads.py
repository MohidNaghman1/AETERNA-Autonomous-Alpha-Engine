"""Merge alembic heads to avoid multi-head deploy failures.

Revision ID: merge_alembic_heads_20260417
Revises: wallet_profiles_data_backfill_20260417, nullable_user_id
Create Date: 2026-04-17 18:55:00.000000

"""

# revision identifiers, used by Alembic.
revision = "merge_alembic_heads_20260417"
down_revision = ("wallet_profiles_data_backfill_20260417", "nullable_user_id")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge revision only: schema/data changes are in parent revisions.
    pass


def downgrade() -> None:
    # No-op for merge revision.
    pass
