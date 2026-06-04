"""OHLCV time-series and periodic fundamentals."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import Timeframe, timeframe_enum


class PriceData(Base):
    """High-volume OHLCV candles. Composite PK prevents duplicate candles.

    Candidate TimescaleDB hypertable / native partition target (see DB README).
    """

    __tablename__ = "price_data"
    __table_args__ = (CheckConstraint("high >= low", name="price_hl"),)

    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), primary_key=True
    )
    tf: Mapped[Timeframe] = mapped_column(timeframe_enum, primary_key=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")


class Fundamentals(Base):
    __tablename__ = "fundamentals"
    __table_args__ = (
        UniqueConstraint("instrument_id", "period", name="uq_fundamentals_period"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(16), nullable=False)
    pe: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    pb: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    roe: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    de_ratio: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    eps: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    revenue_growth: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    captured_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
