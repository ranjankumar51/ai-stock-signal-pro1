"""Backtest run registry.

One row per backtest execution. Lets many runs coexist and keeps their output
(signals/trades/snapshots tagged with backtest_run_id) isolated from live data.
The actual backtest *engine* is not built yet — this is the foundation only.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','RUNNING','COMPLETED','FAILED')",
            name="status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="PENDING")
    period_start: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    weights_version_id: Mapped[int | None] = mapped_column(ForeignKey("config_weights.id"))
    params: Mapped[dict | None] = mapped_column(JSONB)   # selector, timeframes, costs...
    metrics: Mapped[dict | None] = mapped_column(JSONB)  # results when COMPLETED
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    signals: Mapped[list["Signal"]] = relationship(  # noqa: F821
        back_populates="backtest_run"
    )
    trades: Mapped[list["Trade"]] = relationship(  # noqa: F821
        back_populates="backtest_run"
    )
