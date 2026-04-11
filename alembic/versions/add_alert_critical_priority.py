"""Add priority column to alerts table with CRITICAL level support

Revision ID: add_alert_critical_priority
Revises: agent_b_tables
Create Date: 2026-04-06 16:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_alert_critical_priority"
down_revision = "agent_b_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add priority column to alerts table
    op.add_column(
        "alerts",
        sa.Column("priority", sa.String(), default="MEDIUM", nullable=True),
    )
    op.create_index("ix_alerts_priority", "alerts", ["priority"])

    # Set existing alerts based on priority field if it exists, else default to MEDIUM
    op.execute("""
        UPDATE alerts 
        SET priority = 'MEDIUM'
        WHERE priority IS NULL
        """)


def downgrade() -> None:
    op.drop_index("ix_alerts_priority", table_name="alerts")
    op.drop_column("alerts", "priority")
