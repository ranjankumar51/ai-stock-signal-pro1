"""Incremental sync bookmark per (instrument, timeframe).

Lets the historical sync resume from the last stored candle instead of
re-fetching whole ranges (saves API calls and respects rate limits).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import Timeframe, timeframe_enum


class DataSyncState(Base):
    __tablename__ = "data_sync_state"

    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), primary_key=True
    )
    tf: Mapped[Timeframe] = mapped_column(timeframe_enum, primary_key=True)
    last_synced_ts: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
