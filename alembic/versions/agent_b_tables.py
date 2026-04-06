"""Add Agent B (Profiler) tables: wallet_profiles, entities, trade_records

Revision ID: agent_b_tables
Revises: d9e5f2b3c1a6
Create Date: 2026-04-06 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "agent_b_tables"
down_revision = "d9e5f2b3c1a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create wallet_profiles table
    op.create_table(
        "wallet_profiles",
        sa.Column(
            "wallet_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("blockchain", sa.String(), nullable=True),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("entity_name", sa.String(), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=True),
        sa.Column("profitable_trades", sa.Integer(), nullable=True),
        sa.Column("win_rate", sa.Float(), nullable=True),
        sa.Column("avg_return_24h", sa.Float(), nullable=True),
        sa.Column("avg_return_7d", sa.Float(), nullable=True),
        sa.Column("best_trade_return", sa.Float(), nullable=True),
        sa.Column("worst_trade_return", sa.Float(), nullable=True),
        sa.Column("behavior_cluster", sa.String(), nullable=True),
        sa.Column("tier", sa.String(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("activity_frequency", sa.String(), nullable=True),
        sa.Column("last_activity", sa.DateTime(), nullable=True),
        sa.Column("first_seen", sa.DateTime(), nullable=True),
        sa.Column("preferred_tokens", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("favorite_exchanges", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("favorite_dexes", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("wallet_id"),
        sa.UniqueConstraint("address"),
    )
    op.create_index("ix_wallet_profiles_address", "wallet_profiles", ["address"])
    op.create_index("ix_wallet_profiles_entity_type", "wallet_profiles", ["entity_type"])
    op.create_index("ix_wallet_profiles_entity_name", "wallet_profiles", ["entity_name"])
    op.create_index("ix_wallet_profiles_tier", "wallet_profiles", ["tier"])
    op.create_index("ix_wallet_profiles_created_at", "wallet_profiles", ["created_at"])
    op.create_index(
        "ix_tier_win_rate", "wallet_profiles", ["tier", "win_rate"]
    )

    # Create entities table
    op.create_table(
        "entities",
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("wallets", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("twitter_handle", sa.String(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=True),
        sa.Column("verification_sources", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("total_capital_tracked_usd", sa.Float(), nullable=True),
        sa.Column("total_transactions", sa.Integer(), nullable=True),
        sa.Column("reliability_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("entity_id"),
    )
    op.create_index("ix_entities_name", "entities", ["name"])
    op.create_index("ix_entities_entity_type", "entities", ["entity_type"])
    op.create_index("ix_entity_verified", "entities", ["verified"])
    op.create_index("ix_entities_created_at", "entities", ["created_at"])

    # Create trade_records table
    op.create_table(
        "trade_records",
        sa.Column("trade_id", sa.String(), nullable=False),
        sa.Column("wallet_address", sa.String(), nullable=False),
        sa.Column("token_in", sa.String(), nullable=True),
        sa.Column("token_out", sa.String(), nullable=True),
        sa.Column("amount_in", sa.Float(), nullable=True),
        sa.Column("amount_out", sa.Float(), nullable=True),
        sa.Column("usd_value", sa.Float(), nullable=True),
        sa.Column("exchange_or_dex", sa.String(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("is_profitable", sa.Boolean(), nullable=True),
        sa.Column("return_percentage", sa.Float(), nullable=True),
        sa.Column("return_usd", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("trade_id"),
    )
    op.create_index(
        "ix_trade_records_wallet_address", "trade_records", ["wallet_address"]
    )
    op.create_index("ix_trade_records_token_in", "trade_records", ["token_in"])
    op.create_index("ix_trade_records_token_out", "trade_records", ["token_out"])
    op.create_index("ix_trade_records_usd_value", "trade_records", ["usd_value"])
    op.create_index(
        "ix_trade_records_exchange_or_dex", "trade_records", ["exchange_or_dex"]
    )
    op.create_index("ix_trade_records_timestamp", "trade_records", ["timestamp"])
    op.create_index("ix_trade_records_is_profitable", "trade_records", ["is_profitable"])
    op.create_index(
        "ix_wallet_timestamp",
        "trade_records",
        ["wallet_address", "timestamp"],
    )

    # Create entity_profiles table (cached aggregations)
    op.create_table(
        "entity_profiles",
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("entity_name", sa.String(), nullable=True),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("total_wallets", sa.Integer(), nullable=True),
        sa.Column("unique_tokens_traded", sa.Integer(), nullable=True),
        sa.Column("total_trades_across_wallets", sa.Integer(), nullable=True),
        sa.Column("aggregate_win_rate", sa.Float(), nullable=True),
        sa.Column("aggregate_profitable_trades", sa.Integer(), nullable=True),
        sa.Column("best_wallet", sa.String(), nullable=True),
        sa.Column("best_wallet_win_rate", sa.Float(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("prediction_confidence", sa.Float(), nullable=True),
        sa.Column("performance_last_7d", sa.Float(), nullable=True),
        sa.Column("performance_last_30d", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("entity_id"),
    )


def downgrade() -> None:
    op.drop_table("entity_profiles")
    op.drop_table("trade_records")
    op.drop_table("entities")
    op.drop_table("wallet_profiles")
