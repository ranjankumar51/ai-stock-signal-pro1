"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-04

Creates the complete approved schema: enum types, 11 tables, constraints,
indexes (incl. partial/GIN), and the updated_at trigger. Names follow the
metadata naming convention in app/db/base.py so autogenerate stays clean.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# --- enum value definitions ------------------------------------------------
INSTRUMENT_TYPE = ("STOCK", "INDEX")
TIMEFRAME = ("1m", "5m", "15m", "30m", "1h", "1d", "1w")
SIGNAL_TYPE = ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")
SIGNAL_STATUS = ("ACTIVE", "TRIGGERED", "EXPIRED", "CANCELLED", "CLOSED")
TRADE_SIDE = ("LONG", "SHORT")
TRADE_OUTCOME = ("OPEN", "WIN", "LOSS", "BREAKEVEN")
SENTIMENT_LABEL = ("POSITIVE", "NEGATIVE", "NEUTRAL")


def _enum(name: str) -> postgresql.ENUM:
    # create_type=False: types are created explicitly in upgrade() below.
    return postgresql.ENUM(name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    # --- extensions --------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")

    # --- enum types --------------------------------------------------------
    for name, vals in (
        ("instrument_type", INSTRUMENT_TYPE),
        ("timeframe", TIMEFRAME),
        ("signal_type", SIGNAL_TYPE),
        ("signal_status", SIGNAL_STATUS),
        ("trade_side", TRADE_SIDE),
        ("trade_outcome", TRADE_OUTCOME),
        ("sentiment_label", SENTIMENT_LABEL),
    ):
        postgresql.ENUM(*vals, name=name).create(bind, checkfirst=True)

    # --- instruments -------------------------------------------------------
    op.create_table(
        "instruments",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("isin", sa.String(12)),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("instrument_type", _enum("instrument_type"), nullable=False),
        sa.Column("sector", sa.String(64)),
        sa.Column("exchange", sa.String(16), nullable=False, server_default="NSE"),
        sa.Column("broker_token", sa.String(32)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_instruments"),
        sa.UniqueConstraint("symbol", "exchange", name="uq_instruments_symbol_exchange"),
    )

    # --- index_membership --------------------------------------------------
    op.create_table(
        "index_membership",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("index_instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("constituent_instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("weight", sa.Numeric(7, 4)),
        sa.Column("effective_from", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("effective_to", sa.Date()),
        sa.PrimaryKeyConstraint("id", name="pk_index_membership"),
        sa.ForeignKeyConstraint(["index_instrument_id"], ["instruments.id"], ondelete="CASCADE", name="fk_index_membership_index_instrument_id_instruments"),
        sa.ForeignKeyConstraint(["constituent_instrument_id"], ["instruments.id"], ondelete="CASCADE", name="fk_index_membership_constituent_instrument_id_instruments"),
        sa.CheckConstraint("index_instrument_id <> constituent_instrument_id", name="ck_index_membership_membership_not_self"),
        sa.CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_index_membership_membership_dates"),
    )

    # --- price_data --------------------------------------------------------
    op.create_table(
        "price_data",
        sa.Column("instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("tf", _enum("timeframe"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(18, 4), nullable=False),
        sa.Column("high", sa.Numeric(18, 4), nullable=False),
        sa.Column("low", sa.Numeric(18, 4), nullable=False),
        sa.Column("close", sa.Numeric(18, 4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("instrument_id", "tf", "ts", name="pk_price_data"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE", name="fk_price_data_instrument_id_instruments"),
        sa.CheckConstraint("high >= low", name="ck_price_data_price_hl"),
    )

    # --- fundamentals ------------------------------------------------------
    op.create_table(
        "fundamentals",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("period", sa.String(16), nullable=False),
        sa.Column("pe", sa.Numeric(12, 4)),
        sa.Column("pb", sa.Numeric(12, 4)),
        sa.Column("roe", sa.Numeric(12, 4)),
        sa.Column("de_ratio", sa.Numeric(12, 4)),
        sa.Column("eps", sa.Numeric(12, 4)),
        sa.Column("revenue_growth", sa.Numeric(12, 4)),
        sa.Column("market_cap", sa.Numeric(20, 2)),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_fundamentals"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE", name="fk_fundamentals_instrument_id_instruments"),
        sa.UniqueConstraint("instrument_id", "period", name="uq_fundamentals_period"),
    )

    # --- news_items --------------------------------------------------------
    op.create_table(
        "news_items",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("instrument_id", sa.BigInteger()),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("url", sa.String(1024)),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sentiment_score", sa.Numeric(5, 4)),
        sa.Column("sentiment_label", _enum("sentiment_label")),
        sa.Column("summary", sa.Text()),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_news_items"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE", name="fk_news_items_instrument_id_instruments"),
        sa.CheckConstraint("sentiment_score IS NULL OR sentiment_score BETWEEN -1 AND 1", name="ck_news_items_news_sentiment_range"),
    )

    # --- social_items ------------------------------------------------------
    op.create_table(
        "social_items",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("window_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sentiment_score", sa.Numeric(5, 4)),
        sa.Column("mention_volume", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_social_items"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE", name="fk_social_items_instrument_id_instruments"),
        sa.UniqueConstraint("instrument_id", "platform", "window_ts", name="uq_social_bucket"),
        sa.CheckConstraint("sentiment_score IS NULL OR sentiment_score BETWEEN -1 AND 1", name="ck_social_items_social_sentiment_range"),
    )

    # --- config_weights ----------------------------------------------------
    op.create_table(
        "config_weights",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("weights", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_config_weights"),
        sa.UniqueConstraint("version", name="uq_config_weights_version"),
    )

    # --- analysis_snapshots ------------------------------------------------
    op.create_table(
        "analysis_snapshots",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tech_score", sa.Numeric(5, 4)),
        sa.Column("fund_score", sa.Numeric(5, 4)),
        sa.Column("news_score", sa.Numeric(5, 4)),
        sa.Column("social_score", sa.Numeric(5, 4)),
        sa.Column("vol_score", sa.Numeric(5, 4)),
        sa.Column("details", postgresql.JSONB()),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_snapshots"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE", name="fk_analysis_snapshots_instrument_id_instruments"),
        sa.UniqueConstraint("instrument_id", "ts", name="uq_analysis_snapshots_instrument_id_ts"),
    )

    # --- signals -----------------------------------------------------------
    op.create_table(
        "signals",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("snapshot_id", sa.BigInteger()),
        sa.Column("weights_version_id", sa.BigInteger()),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("signal", _enum("signal_type"), nullable=False),
        sa.Column("composite_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("side", _enum("trade_side")),
        sa.Column("entry", sa.Numeric(18, 4)),
        sa.Column("stop_loss", sa.Numeric(18, 4)),
        sa.Column("target", sa.Numeric(18, 4)),
        sa.Column("risk_reward", sa.Numeric(8, 4)),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("status", _enum("signal_status"), nullable=False, server_default="ACTIVE"),
        sa.Column("rationale", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_signals"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE", name="fk_signals_instrument_id_instruments"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["analysis_snapshots.id"], ondelete="SET NULL", name="fk_signals_snapshot_id_analysis_snapshots"),
        sa.ForeignKeyConstraint(["weights_version_id"], ["config_weights.id"], name="fk_signals_weights_version_id_config_weights"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_signals_confidence_range"),
        sa.CheckConstraint("composite_score BETWEEN -1 AND 1", name="ck_signals_composite_range"),
        sa.CheckConstraint("signal = 'HOLD' OR risk_reward IS NULL OR risk_reward >= 2", name="ck_signals_min_risk_reward"),
    )

    # --- trades ------------------------------------------------------------
    op.create_table(
        "trades",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("signal_id", sa.BigInteger(), nullable=False),
        sa.Column("side", _enum("trade_side"), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("entry_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("exit_ts", sa.DateTime(timezone=True)),
        sa.Column("exit_price", sa.Numeric(18, 4)),
        sa.Column("pnl", sa.Numeric(18, 4)),
        sa.Column("outcome", _enum("trade_outcome"), nullable=False, server_default="OPEN"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_trades"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="RESTRICT", name="fk_trades_signal_id_signals"),
        sa.CheckConstraint("qty > 0", name="ck_trades_qty_positive"),
        sa.CheckConstraint("exit_ts IS NULL OR exit_ts >= entry_ts", name="ck_trades_exit_after_entry"),
        sa.CheckConstraint("outcome = 'OPEN' OR (exit_ts IS NOT NULL AND exit_price IS NOT NULL)", name="ck_trades_closed_has_exit"),
    )

    # --- performance -------------------------------------------------------
    op.create_table(
        "performance",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("period", sa.String(16), nullable=False),
        sa.Column("total_signals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Numeric(6, 4)),
        sa.Column("avg_risk_reward", sa.Numeric(8, 4)),
        sa.Column("cumulative_pnl", sa.Numeric(20, 4)),
        sa.Column("sharpe", sa.Numeric(8, 4)),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_performance"),
        sa.UniqueConstraint("period", name="uq_performance_period"),
    )

    # --- audit_log ---------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity", sa.String(64)),
        sa.Column("entity_id", sa.BigInteger()),
        sa.Column("payload", postgresql.JSONB()),
        sa.PrimaryKeyConstraint("id", name="pk_audit_log"),
    )

    # --- indexes (V005) ----------------------------------------------------
    op.create_index("ix_price_data_tf_ts", "price_data", ["tf", sa.text("ts DESC")])
    op.create_index("ix_price_data_instr_tf_ts", "price_data", ["instrument_id", "tf", sa.text("ts DESC")])
    op.create_index("ix_membership_index_active", "index_membership", ["index_instrument_id"], postgresql_where=sa.text("effective_to IS NULL"))
    op.create_index("ix_membership_constituent", "index_membership", ["constituent_instrument_id"])
    op.create_index("ix_fundamentals_instrument", "fundamentals", ["instrument_id", sa.text("captured_at DESC")])
    op.create_index("ix_news_instr_published", "news_items", ["instrument_id", sa.text("published_at DESC")])
    op.create_index("ix_news_published", "news_items", [sa.text("published_at DESC")])
    op.create_index("ix_social_instr_window", "social_items", ["instrument_id", sa.text("window_ts DESC")])
    op.create_index("ix_snapshot_instr_ts", "analysis_snapshots", ["instrument_id", sa.text("ts DESC")])
    op.create_index("ix_signals_instr_ts", "signals", ["instrument_id", sa.text("ts DESC")])
    op.create_index("ix_signals_status_ts", "signals", ["status", sa.text("ts DESC")])
    op.create_index("ix_signals_ts", "signals", [sa.text("ts DESC")])
    op.create_index("ix_signals_active_actionable", "signals", [sa.text("ts DESC")], postgresql_where=sa.text("status = 'ACTIVE' AND signal <> 'HOLD'"))
    op.create_index("ix_signals_rationale_gin", "signals", ["rationale"], postgresql_using="gin")
    op.create_index("ix_trades_signal", "trades", ["signal_id"])
    op.create_index("ix_trades_outcome", "trades", ["outcome"], postgresql_where=sa.text("outcome = 'OPEN'"))
    op.create_index("ix_trades_entry_ts", "trades", [sa.text("entry_ts DESC")])
    op.create_index("ix_audit_ts", "audit_log", [sa.text("ts DESC")])
    op.create_index("ix_audit_entity", "audit_log", ["entity", "entity_id"])

    # single active weight set
    op.create_index("uq_config_weights_single_active", "config_weights", ["is_active"], unique=True, postgresql_where=sa.text("is_active IS TRUE"))

    # --- updated_at trigger ------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        "CREATE TRIGGER trg_instruments_updated_at BEFORE UPDATE ON instruments "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
    )
    op.execute(
        "CREATE TRIGGER trg_trades_updated_at BEFORE UPDATE ON trades "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.execute("DROP TRIGGER IF EXISTS trg_trades_updated_at ON trades")
    op.execute("DROP TRIGGER IF EXISTS trg_instruments_updated_at ON instruments")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    for table in (
        "audit_log",
        "performance",
        "trades",
        "signals",
        "analysis_snapshots",
        "config_weights",
        "social_items",
        "news_items",
        "fundamentals",
        "price_data",
        "index_membership",
        "instruments",
    ):
        op.drop_table(table)

    for name in (
        "sentiment_label",
        "trade_outcome",
        "trade_side",
        "signal_status",
        "signal_type",
        "timeframe",
        "instrument_type",
    ):
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)
