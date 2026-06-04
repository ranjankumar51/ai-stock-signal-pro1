"""snapshot timeframe

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-04

Adds a timeframe (tf) column to analysis_snapshots and widens the natural key
to (instrument_id, tf, ts) so the technical engine can store one snapshot per
timeframe per instant. Reuses the existing ``timeframe`` enum.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Table is empty in practice; add as nullable then enforce NOT NULL.
    op.add_column(
        "analysis_snapshots",
        sa.Column("tf", postgresql.ENUM(name="timeframe", create_type=False), nullable=True),
    )
    op.execute("UPDATE analysis_snapshots SET tf = '1d' WHERE tf IS NULL")
    op.alter_column("analysis_snapshots", "tf", nullable=False)

    op.drop_constraint(
        "uq_analysis_snapshots_instrument_id_ts", "analysis_snapshots", type_="unique"
    )
    op.create_unique_constraint(
        "uq_analysis_snapshots_instrument_id_tf_ts",
        "analysis_snapshots",
        ["instrument_id", "tf", "ts"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_analysis_snapshots_instrument_id_tf_ts", "analysis_snapshots", type_="unique"
    )
    op.create_unique_constraint(
        "uq_analysis_snapshots_instrument_id_ts",
        "analysis_snapshots",
        ["instrument_id", "ts"],
    )
    op.drop_column("analysis_snapshots", "tf")
