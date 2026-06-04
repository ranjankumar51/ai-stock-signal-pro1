"""DataFeed abstraction (point-in-time).

A DataFeed serves candles as of a given instant, never beyond it. The DB-backed
implementation reads price_data with ``ts <= end`` (default end = clock.now()),
so the same feed serves both live and backtest engines — the only difference is
which Clock supplies "now". This is the no-look-ahead guarantee.
"""
from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.dto import Candle
from app.models.enums import Timeframe
from app.repositories.price_repo import PriceRepository
from app.runtime.clock import Clock


class DataFeed(ABC):
    @abstractmethod
    async def get_candles(
        self,
        instrument_id: int,
        tf: Timeframe,
        *,
        end: dt.datetime | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        """Ascending candles with ``ts <= end`` (end defaults to clock.now())."""


class DbDataFeed(DataFeed):
    """Reads point-in-time candles from PostgreSQL. Works in both modes."""

    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock
        self.prices = PriceRepository(session)

    async def get_candles(
        self,
        instrument_id: int,
        tf: Timeframe,
        *,
        end: dt.datetime | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        as_of = end or self.clock.now()
        rows = await self.prices.get_series(instrument_id, tf, end=as_of, limit=limit)
        return [
            Candle(
                ts=r.ts,
                open=r.open,
                high=r.high,
                low=r.low,
                close=r.close,
                volume=r.volume,
            )
            for r in rows
        ]
