"""Data access for instruments."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.dto import ProviderInstrument
from app.models.enums import InstrumentType
from app.models.instrument import Instrument


class InstrumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_many(self, items: list[ProviderInstrument]) -> int:
        if not items:
            return 0
        rows = [
            {
                "symbol": it.symbol,
                "isin": it.isin,
                "name": it.name,
                "instrument_type": it.instrument_type,
                "exchange": it.exchange,
                "broker_token": it.broker_token,
                "is_active": True,
            }
            for it in items
        ]
        total = 0
        for batch in _chunk(rows, 1000):
            stmt = insert(Instrument).values(batch)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_instruments_symbol_exchange",
                set_={
                    "name": stmt.excluded.name,
                    "instrument_type": stmt.excluded.instrument_type,
                    "broker_token": stmt.excluded.broker_token,
                    "isin": stmt.excluded.isin,
                    "is_active": True,
                },
            )
            await self.session.execute(stmt)
            total += len(batch)
        return total

    async def get_by_symbol(self, symbol: str, exchange: str = "NSE") -> Instrument | None:
        res = await self.session.execute(
            select(Instrument).where(
                Instrument.symbol == symbol, Instrument.exchange == exchange
            )
        )
        return res.scalar_one_or_none()

    async def resolve_symbols(
        self, symbols: list[str], exchange: str = "NSE"
    ) -> dict[str, Instrument]:
        if not symbols:
            return {}
        res = await self.session.execute(
            select(Instrument).where(
                Instrument.symbol.in_(symbols), Instrument.exchange == exchange
            )
        )
        return {inst.symbol: inst for inst in res.scalars()}

    async def list_active(
        self, instrument_type: InstrumentType | None = None
    ) -> list[Instrument]:
        stmt = select(Instrument).where(Instrument.is_active.is_(True))
        if instrument_type is not None:
            stmt = stmt.where(Instrument.instrument_type == instrument_type)
        res = await self.session.execute(stmt)
        return list(res.scalars())


def _chunk(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]
