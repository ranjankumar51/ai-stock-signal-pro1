"""Provider interfaces (adapter pattern).

These ABCs are the contract the rest of the system codes against. Swapping
Zerodha for Upstox/Angel One (or adding a fundamentals/news vendor) means
writing a new adapter that satisfies the relevant interface — no caller
changes. Phase 1 implements only :class:`MarketDataProvider` (Zerodha).
"""
from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod

from app.ingestion.dto import Candle, ProviderInstrument, QuoteTick
from app.models.enums import Timeframe


class MarketDataProvider(ABC):
    """Instruments, OHLCV history, and live quotes."""

    name: str = "abstract"

    @abstractmethod
    def is_configured(self) -> bool:
        """True if credentials/session are present and usable."""

    @abstractmethod
    async def fetch_instruments(self, exchange: str = "NSE") -> list[ProviderInstrument]:
        ...

    @abstractmethod
    async def fetch_ohlcv(
        self,
        broker_token: str,
        tf: Timeframe,
        start: dt.datetime,
        end: dt.datetime,
    ) -> list[Candle]:
        """Return candles in [start, end]. Implementations chunk as needed and
        respect provider rate limits. ``start``/``end`` are UTC-aware."""

    @abstractmethod
    async def fetch_quotes(self, broker_tokens: list[str]) -> list[QuoteTick]:
        ...


class FundamentalsProvider(ABC):
    """Periodic fundamentals. Not implemented in Phase 1."""

    name: str = "abstract"

    @abstractmethod
    async def fetch_fundamentals(self, symbol: str) -> dict:
        ...


class NewsProvider(ABC):
    """Headline/news feed. Not implemented in Phase 1."""

    name: str = "abstract"

    @abstractmethod
    async def fetch_news(
        self, symbol: str | None, since: dt.datetime
    ) -> list[dict]:
        ...
