"""Ingestion facade.

The single entry point the worker (scheduler + queue consumer) calls. It owns
the provider instance (and therefore the rate limiters) and opens a DB session
per operation. Because only the worker constructs this, all Kite access is
funnelled through one process with authoritative rate limiting.
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.core.redis import get_client
from app.db.session import SessionLocal
from app.ingestion.intervals import PHASE1_TIMEFRAMES
from app.ingestion.providers.base import MarketDataProvider
from app.ingestion.providers.factory import get_market_data_provider
from app.models.enums import InstrumentType, Timeframe
from app.repositories.instrument_repo import InstrumentRepository
from app.services.historical_sync import HistoricalSyncService
from app.services.instrument_sync import InstrumentSyncService
from app.services.market_data import MarketDataService

log = get_logger(__name__)


class IngestionService:
    def __init__(self, provider: MarketDataProvider | None = None) -> None:
        self.provider = provider or get_market_data_provider()

    def _configured(self) -> bool:
        if not self.provider.is_configured():
            log.warning("ingestion.provider_unconfigured", provider=self.provider.name)
            return False
        return True

    async def run_sync_instruments(self, also_constituents: bool = True) -> None:
        if not self._configured():
            return
        async with SessionLocal() as session:
            svc = InstrumentSyncService(session, self.provider)
            await svc.sync_master()
            if also_constituents:
                await svc.sync_constituents()

    async def run_sync_constituents(self) -> None:
        if not self._configured():
            return
        async with SessionLocal() as session:
            svc = InstrumentSyncService(session, self.provider)
            await svc.sync_constituents()

    async def run_sync_historical(self, params: dict) -> dict | None:
        if not self._configured():
            return None
        timeframes = _parse_timeframes(params.get("timeframes"))
        async with SessionLocal() as session:
            svc = HistoricalSyncService(
                session, self.provider, MarketDataService(get_client())
            )
            return await svc.sync(
                selector=params.get("selector"),
                symbols=params.get("symbols"),
                timeframes=timeframes,
                lookback_days=params.get("lookback_days"),
            )

    async def run_refresh_quotes(self) -> None:
        if not self._configured():
            return
        market_data = MarketDataService(get_client())
        async with SessionLocal() as session:
            repo = InstrumentRepository(session)
            stocks = await repo.list_active(InstrumentType.STOCK)
            indices = await repo.list_active(InstrumentType.INDEX)
        universe = [i for i in (*stocks, *indices) if i.broker_token]
        if not universe:
            return
        by_token = {i.broker_token: i.symbol for i in universe}
        ticks = await self.provider.fetch_quotes(list(by_token.keys()))
        for tick in ticks:
            symbol = by_token.get(tick.broker_token)
            if symbol:
                await market_data.cache_quote(symbol, tick.last_price, tick.ts)
        log.info("quotes.refreshed", count=len(ticks))


def _parse_timeframes(values: list[str] | None) -> list[Timeframe]:
    if not values:
        return list(PHASE1_TIMEFRAMES)
    out: list[Timeframe] = []
    for v in values:
        try:
            out.append(Timeframe(v))
        except ValueError:
            out.append(Timeframe[v])
    return out
