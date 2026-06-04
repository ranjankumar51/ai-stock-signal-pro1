"""Data access for OHLCV candles."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.dto import Candle
from app.models.enums import Timeframe
from app.models.market_data import PriceData


class PriceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_candles(
        self, instrument_id: int, tf: Timeframe, candles: list[Candle]
    ) -> int:
        if not candles:
            return 0
        rows = [
            {
                "instrument_id": instrument_id,
                "tf": tf,
                "ts": c.ts,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ]
        total = 0
        for batch in _chunk(rows, 1000):
            stmt = insert(PriceData).values(batch)
            stmt = stmt.on_conflict_do_update(
                constraint="pk_price_data",
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                },
            )
            await self.session.execute(stmt)
            total += len(batch)
        return total

    async def get_latest(self, instrument_id: int, tf: Timeframe) -> PriceData | None:
        res = await self.session.execute(
            select(PriceData)
            .where(PriceData.instrument_id == instrument_id, PriceData.tf == tf)
            .order_by(PriceData.ts.desc())
            .limit(1)
        )
        return res.scalar_one_or_none()

    async def get_series(
        self,
        instrument_id: int,
        tf: Timeframe,
        end: dt.datetime | None = None,
        limit: int | None = None,
    ) -> list[PriceData]:
        """Point-in-time window ending at ``end``, returned ascending by ts.

        Uses the (instrument_id, tf, ts DESC) index: fetch the newest ``limit``
        rows at or before ``end`` then reverse to chronological order — this is
        the performance-critical read for indicator computation, so we bound it
        to only the candles the indicators need rather than scanning history.
        """
        stmt = select(PriceData).where(
            PriceData.instrument_id == instrument_id, PriceData.tf == tf
        )
        if end is not None:
            stmt = stmt.where(PriceData.ts <= end)
        stmt = stmt.order_by(PriceData.ts.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        res = await self.session.execute(stmt)
        rows = list(res.scalars())
        rows.reverse()  # chronological
        return rows


def _chunk(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]
