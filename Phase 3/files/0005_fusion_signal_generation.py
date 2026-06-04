"""fusion signal generation

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-04

Phase 3. Adds the timeframe (tf) column to ``signals`` so signals are keyed
point-in-time per timeframe, adds idempotency guards (partial unique indexes
for LIVE and BACKTEST), a read index, and seeds the default active fusion
weight set (version 1). Reuses the existing ``timeframe`` enum.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_WEIGHTS_JSON = (
    '{"technical": 0.40, "fundamental": 0.20, "news": 0.15, '
    '"social": 0.10, "volatility": 0.15}'
)


def upgrade() -> None:
    # --- signals.tf (table empty in practice; add nullable then enforce) ----
    op.add_column(
        "signals",
        sa.Column("tf", postgresql.ENUM(name="timeframe", create_type=False), nullable=True),
    )
    op.execute("UPDATE signals SET tf = '1d' WHERE tf IS NULL")
    op.alter_column("signals", "tf", nullable=False)

    op.create_index("ix_signals_instr_tf_ts", "signals", ["instrument_id", "tf", sa.text("ts DESC")])

    # --- idempotency: one signal per point-in-time key, per mode -------------
    op.execute(
        "CREATE UNIQUE INDEX uq_signals_live_pit ON signals (instrument_id, tf, ts) "
        "WHERE mode = 'LIVE' AND backtest_run_id IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_signals_bt_pit ON signals (instrument_id, tf, ts, backtest_run_id) "
        "WHERE backtest_run_id IS NOT NULL"
    )

    # --- seed default fusion weights (version 1, active) ---------------------
    op.execute(
        "INSERT INTO config_weights (version, weights, is_active, notes) VALUES "
        f"(1, '{DEFAULT_WEIGHTS_JSON}'::jsonb, true, "
        "'Phase 3 default fusion weights (only technical active)') "
        "ON CONFLICT (version) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM config_weights WHERE version = 1")
    op.execute("DROP INDEX IF EXISTS uq_signals_bt_pit")
    op.execute("DROP INDEX IF EXISTS uq_signals_live_pit")
    op.drop_index("ix_signals_instr_tf_ts", table_name="signals")
    op.drop_column("signals", "tf")
