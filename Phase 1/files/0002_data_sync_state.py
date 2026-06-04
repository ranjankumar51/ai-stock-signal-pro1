"""data_sync_state

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-04

Adds the incremental-sync bookmark table. Reuses the existing ``timeframe``
enum (does not recreate it).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "data_sync_state",
        sa.Column("instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("tf", postgresql.ENUM(name="timeframe", create_type=False), nullable=False),
        sa.Column("last_synced_ts", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("instrument_id", "tf", name="pk_data_sync_state"),
        sa.ForeignKeyConstraint(
            ["instrument_id"], ["instruments.id"], ondelete="CASCADE",
            name="fk_data_sync_state_instrument_id_instruments",
        ),
    )


def downgrade() -> None:
    op.drop_table("data_sync_state")
