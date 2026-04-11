"""Make alerts.user_id nullable for system/broadcast alerts.

Revision ID: nullable_user_id
Revises: d9e5f2b3c1a6
Create Date: 2026-04-06 14:30:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "nullable_user_id"
down_revision = "88485d2f1c74"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make user_id nullable for system/broadcast alerts
    op.alter_column("alerts", "user_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    # Revert: set user_id to NOT NULL
    op.alter_column("alerts", "user_id", existing_type=sa.Integer(), nullable=False)
