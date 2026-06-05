"""risk management

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-04

Phase 4. Adds the RISK_REJECTED label to the existing ``signal_status`` enum and
two dedicated risk columns to ``signals`` (position_size, risk_confidence). The
entry / stop_loss / target / risk_reward columns already exist (Phase 0), so no
new columns are needed for those. Additive and reversible (the enum label
cannot be removed by PostgreSQL on downgrade — documented below).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New terminal status for signals whose risk plan fails validation. PG16
    # allows ADD VALUE inside a transaction as long as it isn't *used* in the
    # same transaction (we only add columns here).
    op.execute("ALTER TYPE signal_status ADD VALUE IF NOT EXISTS 'RISK_REJECTED'")

    op.add_column("signals", sa.Column("position_size", sa.Numeric(18, 4)))
    op.add_column("signals", sa.Column("risk_confidence", sa.Numeric(5, 4)))

    op.create_check_constraint(
        "ck_signals_risk_confidence_range",
        "signals",
        "risk_confidence IS NULL OR risk_confidence BETWEEN 0 AND 1",
    )
    op.create_check_constraint(
        "ck_signals_position_size_positive",
        "signals",
        "position_size IS NULL OR position_size > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_signals_position_size_positive", "signals", type_="check")
    op.drop_constraint("ck_signals_risk_confidence_range", "signals", type_="check")
    op.drop_column("signals", "risk_confidence")
    op.drop_column("signals", "position_size")
    # NOTE: PostgreSQL cannot drop a single enum value; the 'RISK_REJECTED'
    # label is intentionally left on signal_status (harmless, additive).
