"""Scoring layer tables: versioned weights, analysis snapshots, and signals.

These tables hold *outputs*; the fusion/scoring logic that writes them is out
of scope for Phase 0.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    SignalStatus,
    SignalType,
    TradeSide,
    signal_status_enum,
    signal_type_enum,
    trade_side_enum,
)


class ConfigWeights(Base):
    __tablename__ = "config_weights"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AnalysisSnapshot(Base):
    __tablename__ = "analysis_snapshots"
    __table_args__ = (
        UniqueConstraint("instrument_id", "ts", name="uq_analysis_snapshots_instrument_id_ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False
    )
    ts: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    tech_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    fund_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    news_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    social_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    vol_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    details: Mapped[dict | None] = mapped_column(JSONB)


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1", name="confidence_range"),
        CheckConstraint("composite_score BETWEEN -1 AND 1", name="composite_range"),
        CheckConstraint(
            "signal = 'HOLD' OR risk_reward IS NULL OR risk_reward >= 2",
            name="min_risk_reward",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("analysis_snapshots.id", ondelete="SET NULL")
    )
    weights_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("config_weights.id")
    )
    ts: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    signal: Mapped[SignalType] = mapped_column(signal_type_enum, nullable=False)
    composite_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    side: Mapped[TradeSide | None] = mapped_column(trade_side_enum)
    entry: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    target: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    risk_reward: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    valid_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[SignalStatus] = mapped_column(
        signal_status_enum, nullable=False, server_default="ACTIVE"
    )
    rationale: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    instrument: Mapped["Instrument"] = relationship(  # noqa: F821
        back_populates="signals"
    )
    trades: Mapped[list["Trade"]] = relationship(  # noqa: F821
        back_populates="signal"
    )
