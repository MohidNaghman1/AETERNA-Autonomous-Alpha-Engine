"""Make alert user_id and event_id nullable for system alerts

Revision ID: d9e5f2b3c1a6
Revises: c8f4d9e2b1a5
Create Date: 2026-03-13 07:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d9e5f2b3c1a6"
down_revision: Union[str, Sequence[str], None] = "99627ce2eeb8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - make alert user_id and event_id nullable."""
    # Alter user_id constraint
    op.alter_column(
        'alerts',
        'user_id',
        existing_type=sa.Integer(),
        nullable=True,
        existing_nullable=False,
    )
    
    # Alter event_id constraint
    op.alter_column(
        'alerts',
        'event_id',
        existing_type=sa.Integer(),
        nullable=True,
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema - make alert user_id and event_id not nullable."""
    # Revert user_id - set default for existing nulls first
    op.execute("UPDATE alerts SET user_id = 0 WHERE user_id IS NULL")
    op.alter_column(
        'alerts',
        'user_id',
        existing_type=sa.Integer(),
        nullable=False,
        existing_nullable=True,
    )
    
    # Revert event_id - set default for existing nulls first
    op.execute("UPDATE alerts SET event_id = 0 WHERE event_id IS NULL")
    op.alter_column(
        'alerts',
        'event_id',
        existing_type=sa.Integer(),
        nullable=False,
        existing_nullable=True,
    )
