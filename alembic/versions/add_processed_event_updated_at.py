"""Add updated_at column to processed_events for Agent B profiling tracking

Revision ID: add_processed_event_updated_at
Revises: add_alert_critical_priority
Create Date: 2026-04-06 16:30:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_processed_event_updated_at"
down_revision = "add_alert_critical_priority"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add updated_at column to processed_events
    op.add_column(
        "processed_events",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_processed_events_updated_at",
        "processed_events",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_processed_events_updated_at", table_name="processed_events")
    op.drop_column("processed_events", "updated_at")
