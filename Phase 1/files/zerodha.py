"""Zerodha Kite Connect adapter (MarketDataProvider).

Design notes:
  * The kiteconnect SDK is synchronous, so every call is offloaded with
    ``asyncio.to_thread`` to avoid blocking the event loop.
  * Rate limits are enforced with in-process token-bucket limiters
    (historical 3/s, quote 1/s). Because the worker is the only process that
    instantiates this adapter, these limiters are authoritative.
  * Transient failures (network, 429, upstream data errors) are retried with
    exponential backoff via tenacity.
  * Kite caps the date range per historical request by interval; long ranges
    are chunked automatically (see intervals.MAX_DAYS_PER_REQUEST).
  * Kite speaks IST; inputs are converted from UTC and outputs back to UTC.
"""
from __future__ import annotations

import asyncio
import datetime as dt
from decimal import Decimal
from zoneinfo import ZoneInfo

from aiolimiter import AsyncLimiter
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import get_logger
from app.ingestion.dto import Candle, ProviderInstrument, QuoteTick
from app.ingestion.intervals import KITE_INTERVAL, MAX_DAYS_PER_REQUEST
from app.ingestion.providers.base import MarketDataProvider
from app.models.enums import InstrumentType, Timeframe

log = get_logger(__name__)
IST = ZoneInfo("Asia/Kolkata")
UTC = dt.timezone.utc

try:  # SDK + its exception types are optional at import time
    from kiteconnect import KiteConnect
    from kiteconnect.exceptions import DataException, NetworkException

    _RETRYABLE: tuple[type[Exception], ...] = (
        NetworkException,
        DataException,
        ConnectionError,
        TimeoutError,
    )
    _SDK_AVAILABLE = True
except Exception:  # pragma: no cover - SDK not installed
    KiteConnect = None  # type: ignore[assignment]
    _RETRYABLE = (ConnectionError, TimeoutError)
    _SDK_AVAILABLE = False


_retry = retry(
    retry=retry_if_exception_type(_RETRYABLE),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
    reraise=True,
)


class ZerodhaProvider(MarketDataProvider):
    name = "zerodha"

    def __init__(self) -> None:
        self._historical_limiter = AsyncLimiter(3, 1)  # 3 req / sec
        self._quote_limiter = AsyncLimiter(1, 1)  # 1 req / sec
        self._kite = None
        if (
            _SDK_AVAILABLE
            and settings.zerodha_api_key
            and settings.zerodha_access_token
        ):
            self._kite = KiteConnect(api_key=settings.zerodha_api_key)
            self._kite.set_access_token(settings.zerodha_access_token)

    def is_configured(self) -> bool:
        return self._kite is not None

    def _require(self):
        if self._kite is None:
            raise RuntimeError(
                "Zerodha provider not configured: set ZERODHA_API_KEY and "
                "ZERODHA_ACCESS_TOKEN (daily token from Kite login)."
            )
        return self._kite

    # --- instruments ---------------------------------------------------
    async def fetch_instruments(self, exchange: str = "NSE") -> list[ProviderInstrument]:
        kite = self._require()
        raw = await asyncio.to_thread(self._instruments_call, kite, exchange)
        out: list[ProviderInstrument] = []
        for row in raw:
            seg = row.get("segment")
            itype = row.get("instrument_type")
            if seg == "INDICES":
                kind = InstrumentType.INDEX
            elif itype == "EQ":
                kind = InstrumentType.STOCK
            else:
                continue  # skip F&O, currencies, etc. for Phase 1
            out.append(
                ProviderInstrument(
                    symbol=row["tradingsymbol"],
                    name=row.get("name") or row["tradingsymbol"],
                    instrument_type=kind,
                    exchange=row.get("exchange", exchange),
                    broker_token=str(row["instrument_token"]),
                    segment=seg,
                )
            )
        log.info("zerodha.instruments_fetched", exchange=exchange, count=len(out))
        return out

    @_retry
    def _instruments_call(self, kite, exchange: str) -> list[dict]:
        return kite.instruments(exchange)

    # --- OHLCV ---------------------------------------------------------
    async def fetch_ohlcv(
        self, broker_token: str, tf: Timeframe, start: dt.datetime, end: dt.datetime
    ) -> list[Candle]:
        kite = self._require()
        interval = KITE_INTERVAL[tf]
        max_days = MAX_DAYS_PER_REQUEST[tf]
        token = int(broker_token)

        candles: list[Candle] = []
        chunk_start = start
        while chunk_start < end:
            chunk_end = min(chunk_start + dt.timedelta(days=max_days), end)
            async with self._historical_limiter:
                rows = await asyncio.to_thread(
                    self._historical_call, kite, token, interval, chunk_start, chunk_end
                )
            candles.extend(self._to_candles(rows))
            chunk_start = chunk_end
        log.info(
            "zerodha.ohlcv_fetched",
            token=broker_token,
            tf=tf.value,
            candles=len(candles),
        )
        return candles

    @_retry
    def _historical_call(self, kite, token, interval, start, end) -> list[dict]:
        return kite.historical_data(
            instrument_token=token,
            from_date=start.astimezone(IST).replace(tzinfo=None),
            to_date=end.astimezone(IST).replace(tzinfo=None),
            interval=interval,
            continuous=False,
            oi=False,
        )

    @staticmethod
    def _to_candles(rows: list[dict]) -> list[Candle]:
        out: list[Candle] = []
        for r in rows:
            ts = r["date"]
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=IST)
            out.append(
                Candle(
                    ts=ts.astimezone(UTC),
                    open=Decimal(str(r["open"])),
                    high=Decimal(str(r["high"])),
                    low=Decimal(str(r["low"])),
                    close=Decimal(str(r["close"])),
                    volume=int(r.get("volume") or 0),
                )
            )
        return out

    # --- quotes --------------------------------------------------------
    async def fetch_quotes(self, broker_tokens: list[str]) -> list[QuoteTick]:
        kite = self._require()
        if not broker_tokens:
            return []
        tokens = [int(t) for t in broker_tokens]
        async with self._quote_limiter:
            raw = await asyncio.to_thread(self._quote_call, kite, tokens)
        ticks: list[QuoteTick] = []
        for key, q in raw.items():
            ts = q.get("timestamp") or q.get("last_trade_time")
            if ts is None:
                ts = dt.datetime.now(tz=IST)
            elif ts.tzinfo is None:
                ts = ts.replace(tzinfo=IST)
            ticks.append(
                QuoteTick(
                    broker_token=str(key),
                    last_price=Decimal(str(q["last_price"])),
                    ts=ts.astimezone(UTC),
                )
            )
        return ticks

    @_retry
    def _quote_call(self, kite, tokens: list[int]) -> dict:
        # Kite accepts up to 500 instruments per quote() call.
        return kite.quote(tokens)
