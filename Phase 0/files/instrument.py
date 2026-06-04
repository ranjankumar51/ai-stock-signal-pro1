"""Instrument universe and index membership."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import InstrumentType, instrument_type_enum


class Instrument(Base):
    __tablename__ = "instruments"
    __table_args__ = (
        UniqueConstraint("symbol", "exchange", name="uq_instruments_symbol_exchange"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    isin: Mapped[str | None] = mapped_column(String(12))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    instrument_type: Mapped[InstrumentType] = mapped_column(
        instrument_type_enum, nullable=False
    )
    sector: Mapped[str | None] = mapped_column(String(64))
    exchange: Mapped[str] = mapped_column(String(16), nullable=False, server_default="NSE")
    broker_token: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # String forward-ref resolved via SQLAlchemy's class registry (see models/__init__.py).
    signals: Mapped[list["Signal"]] = relationship(  # noqa: F821
        back_populates="instrument"
    )


class IndexMembership(Base):
    __tablename__ = "index_membership"
    __table_args__ = (
        CheckConstraint(
            "index_instrument_id <> constituent_instrument_id",
            name="membership_not_self",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="membership_dates",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    index_instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False
    )
    constituent_instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False
    )
    weight: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    effective_from: Mapped[dt.date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    effective_to: Mapped[dt.date | None] = mapped_column(Date)
