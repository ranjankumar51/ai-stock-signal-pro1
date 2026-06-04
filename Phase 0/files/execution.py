"""Trade execution records and rolled-up performance metrics."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    TradeOutcome,
    TradeSide,
    trade_outcome_enum,
    trade_side_enum,
)


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        CheckConstraint("qty > 0", name="qty_positive"),
        CheckConstraint(
            "exit_ts IS NULL OR exit_ts >= entry_ts", name="exit_after_entry"
        ),
        CheckConstraint(
            "outcome = 'OPEN' OR (exit_ts IS NOT NULL AND exit_price IS NOT NULL)",
            name="closed_has_exit",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    signal_id: Mapped[int] = mapped_column(
        ForeignKey("signals.id", ondelete="RESTRICT"), nullable=False
    )
    side: Mapped[TradeSide] = mapped_column(trade_side_enum, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_ts: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    exit_ts: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    outcome: Mapped[TradeOutcome] = mapped_column(
        trade_outcome_enum, nullable=False, server_default="OPEN"
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    signal: Mapped["Signal"] = relationship(back_populates="trades")  # noqa: F821


class Performance(Base):
    __tablename__ = "performance"
    __table_args__ = (
        UniqueConstraint("period", name="uq_performance_period"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    period: Mapped[str] = mapped_column(String(16), nullable=False)
    total_signals: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    total_trades: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    win_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    avg_risk_reward: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    cumulative_pnl: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    sharpe: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    computed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
