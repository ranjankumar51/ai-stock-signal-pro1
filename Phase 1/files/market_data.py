"""Market-data reads and hot-cache writes.

The API uses this (read path) to serve latest candles/quotes from Redis with a
DB fallback. The worker uses the cache-write methods after each sync.
"""
from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.ingestion.dto import Candle
from app.models.enums import Timeframe
from app.repositories.instrument_repo import InstrumentRepository
from app.repositories.price_repo import PriceRepository

log = get_logger(__name__)


def _candle_key(symbol: str, tf: Timeframe) -> str:
    return f"md:candle:{symbol}:{tf.value}"


def _quote_key(symbol: str) -> str:
    return f"md:quote:{symbol}"


class MarketDataService:
    def __init__(self, redis_client: redis.Redis, session: AsyncSession | None = None) -> None:
        self.redis = redis_client
        self.session = session

    # --- cache writes (worker) ----------------------------------------
    async def cache_candle(self, symbol: str, tf: Timeframe, candle: Candle) -> None:
        payload = {
            "symbol": symbol,
            "tf": tf.value,
            "ts": candle.ts.isoformat(),
            "open": str(candle.open),
            "high": str(candle.high),
            "low": str(candle.low),
            "close": str(candle.close),
            "volume": candle.volume,
            "source": "cache",
        }
        await self.redis.set(
            _candle_key(symbol, tf), json.dumps(payload), ex=settings.cache_latest_ttl
        )

    async def cache_quote(self, symbol: str, last_price: Decimal, ts: dt.datetime) -> None:
        payload = {"symbol": symbol, "last_price": str(last_price), "ts": ts.isoformat()}
        await self.redis.set(
            _quote_key(symbol), json.dumps(payload), ex=settings.cache_quote_ttl
        )

    # --- read path (API) ----------------------------------------------
    async def get_latest_candle(self, symbol: str, tf: Timeframe) -> dict | None:
        cached = await self.redis.get(_candle_key(symbol, tf))
        if cached:
            return json.loads(cached)

        if self.session is None:
            return None
        inst = await InstrumentRepository(self.session).get_by_symbol(symbol)
        if inst is None:
            return None
        row = await PriceRepository(self.session).get_latest(inst.id, tf)
        if row is None:
            return None
        payload = {
            "symbol": symbol,
            "tf": tf.value,
            "ts": row.ts.isoformat(),
            "open": str(row.open),
            "high": str(row.high),
            "low": str(row.low),
            "close": str(row.close),
            "volume": row.volume,
            "source": "db",
        }
        # warm the cache for subsequent reads
        await self.redis.set(
            _candle_key(symbol, tf), json.dumps({**payload, "source": "cache"}),
            ex=settings.cache_latest_ttl,
        )
        return payload

    async def get_latest_quote(self, symbol: str) -> dict | None:
        cached = await self.redis.get(_quote_key(symbol))
        return json.loads(cached) if cached else None
