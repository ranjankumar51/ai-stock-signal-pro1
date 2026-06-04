"""backtest foundation

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-04

Adds the execution_mode enum, the backtest_runs table, and mode +
backtest_run_id columns to signals, trades, and analysis_snapshots so backtest
output can coexist with (and be isolated from) live data.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MODE = ("LIVE", "BACKTEST")


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*MODE, name="execution_mode").create(bind, checkfirst=True)
    mode_enum = postgresql.ENUM(name="execution_mode", create_type=False)

    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("name", sa.String(128)),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column("period_end", sa.DateTime(timezone=True)),
        sa.Column("weights_version_id", sa.BigInteger()),
        sa.Column("params", postgresql.JSONB()),
        sa.Column("metrics", postgresql.JSONB()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id", name="pk_backtest_runs"),
        sa.ForeignKeyConstraint(
            ["weights_version_id"], ["config_weights.id"],
            name="fk_backtest_runs_weights_version_id_config_weights",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING','RUNNING','COMPLETED','FAILED')",
            name="ck_backtest_runs_status_valid",
        ),
    )

    for table in ("signals", "trades", "analysis_snapshots"):
        op.add_column(
            table,
            sa.Column("mode", mode_enum, nullable=False, server_default="LIVE"),
        )
        op.add_column(table, sa.Column("backtest_run_id", sa.BigInteger()))
        op.create_foreign_key(
            f"fk_{table}_backtest_run_id_backtest_runs",
            table,
            "backtest_runs",
            ["backtest_run_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(
            f"ix_{table}_backtest_run_id",
            table,
            ["backtest_run_id"],
            postgresql_where=sa.text("backtest_run_id IS NOT NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("analysis_snapshots", "trades", "signals"):
        op.drop_index(f"ix_{table}_backtest_run_id", table_name=table)
        op.drop_constraint(f"fk_{table}_backtest_run_id_backtest_runs", table, type_="foreignkey")
        op.drop_column(table, "backtest_run_id")
        op.drop_column(table, "mode")
    op.drop_table("backtest_runs")
    postgresql.ENUM(name="execution_mode").drop(bind, checkfirst=True)
