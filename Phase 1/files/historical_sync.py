"""Historical OHLCV synchronization.

Resolves the target universe (an index's constituents, a symbol list, or all
active instruments), then for each (instrument, timeframe) fetches candles from
the last sync bookmark forward, upserts them, advances the bookmark, and warms
the hot cache with the newest candle.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.ingestion.constituents import SELECTOR_ALL, SELECTOR_TO_INDEX
from app.ingestion.providers.base import MarketDataProvider
from app.models.enums import Timeframe
from app.models.instrument import Instrument
from app.repositories.instrument_repo import InstrumentRepository
from app.repositories.membership_repo import MembershipRepository
from app.repositories.price_repo import PriceRepository
from app.repositories.sync_state_repo import SyncStateRepository
from app.services.market_data import MarketDataService

log = get_logger(__name__)
UTC = dt.timezone.utc


class HistoricalSyncService:
    def __init__(
        self,
        session: AsyncSession,
        provider: MarketDataProvider,
        market_data: MarketDataService,
    ) -> None:
        self.session = session
        self.provider = provider
        self.market_data = market_data
        self.instruments = InstrumentRepository(session)
        self.membership = MembershipRepository(session)
        self.prices = PriceRepository(session)
        self.sync_state = SyncStateRepository(session)

    async def resolve_universe(
        self, selector: str | None, symbols: list[str] | None
    ) -> list[Instrument]:
        if symbols:
            resolved = await self.instruments.resolve_symbols(symbols)
            return list(resolved.values())

        sel = (selector or SELECTOR_ALL).upper()
        if sel == SELECTOR_ALL:
            return await self.instruments.list_active()

        index_symbol = SELECTOR_TO_INDEX.get(sel)
        if index_symbol is None:
            raise ValueError(f"Unknown selector: {selector!r}")

        universe: list[Instrument] = []
        index_inst = await self.instruments.get_by_symbol(index_symbol)
        if index_inst is not None:
            universe.append(index_inst)  # include the index itself
        cids = await self.membership.constituent_instrument_ids(index_symbol)
        for inst in await self.instruments.list_active():
            if inst.id in cids:
                universe.append(inst)
        return universe

    async def sync(
        self,
        selector: str | None = None,
        symbols: list[str] | None = None,
        timeframes: list[Timeframe] | None = None,
        lookback_days: int | None = None,
        start: dt.datetime | None = None,
        end: dt.datetime | None = None,
    ) -> dict:
        timeframes = timeframes or [Timeframe.D1]
        universe = await self.resolve_universe(selector, symbols)
        now = dt.datetime.now(tz=UTC)
        end = end or now
        lookback = dt.timedelta(days=lookback_days or settings.default_lookback_days)

        result = {"instruments": len(universe), "candles_upserted": 0, "skipped": 0}

        for inst in universe:
            if not inst.broker_token:
                log.warning("ohlcv.no_broker_token", symbol=inst.symbol)
                result["skipped"] += 1
                continue

            for tf in timeframes:
                window_start = start
                if window_start is None:
                    last = await self.sync_state.get_last_synced(inst.id, tf)
                    window_start = last if last is not None else end - lookback

                if window_start >= end:
                    continue

                candles = await self.provider.fetch_ohlcv(
                    inst.broker_token, tf, window_start, end
                )
                if not candles:
                    continue

                n = await self.prices.upsert_candles(inst.id, tf, candles)
                newest = max(candles, key=lambda c: c.ts)
                await self.sync_state.set_last_synced(inst.id, tf, newest.ts)
                await self.market_data.cache_candle(inst.symbol, tf, newest)
                await self.session.commit()  # checkpoint progress per instrument/tf
                result["candles_upserted"] += n

        log.info("ohlcv.sync_complete", **result)
        return result
