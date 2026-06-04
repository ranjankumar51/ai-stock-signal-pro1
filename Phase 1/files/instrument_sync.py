"""Instrument master + index constituent synchronization."""
from __future__ import annotations

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.ingestion.constituents import CONSTITUENTS, INDEX_DEFINITIONS
from app.ingestion.providers.base import MarketDataProvider
from app.repositories.instrument_repo import InstrumentRepository
from app.repositories.membership_repo import MembershipRepository

log = get_logger(__name__)


class InstrumentSyncService:
    def __init__(self, session: AsyncSession, provider: MarketDataProvider) -> None:
        self.session = session
        self.provider = provider
        self.instruments = InstrumentRepository(session)
        self.membership = MembershipRepository(session)

    async def sync_master(self, exchange: str = "NSE") -> int:
        items = await self.provider.fetch_instruments(exchange)
        count = await self.instruments.upsert_many(items)
        await self.session.commit()
        log.info("instruments.master_synced", exchange=exchange, upserted=count)
        return count

    async def sync_constituents(self) -> dict:
        """Reconcile index_membership against the configured constituent lists."""
        today = dt.date.today()
        summary: dict[str, dict] = {}

        for idx in INDEX_DEFINITIONS:
            index_symbol = idx["symbol"]
            index_inst = await self.instruments.get_by_symbol(index_symbol)
            if index_inst is None:
                log.warning("constituents.index_missing", index=index_symbol)
                summary[index_symbol] = {"error": "index instrument not found"}
                continue

            desired = CONSTITUENTS.get(index_symbol, [])
            resolved = await self.instruments.resolve_symbols(desired)
            missing = sorted(set(desired) - set(resolved))
            if missing:
                log.warning(
                    "constituents.unresolved", index=index_symbol, symbols=missing
                )

            desired_ids = {inst.id for inst in resolved.values()}
            active_ids = await self.membership.active_constituent_ids(index_inst.id)

            to_add = desired_ids - active_ids
            to_close = active_ids - desired_ids
            for cid in to_add:
                await self.membership.add(index_inst.id, cid)
            for cid in to_close:
                await self.membership.close(index_inst.id, cid, today)

            await self.session.commit()
            summary[index_symbol] = {
                "added": len(to_add),
                "closed": len(to_close),
                "active": len(desired_ids),
                "unresolved": missing,
            }
            log.info("constituents.synced", index=index_symbol, **summary[index_symbol])

        return summary
