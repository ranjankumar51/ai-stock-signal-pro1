"""Data access for index membership (temporal many-to-many)."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instrument import IndexMembership, Instrument


class MembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def active_constituent_ids(self, index_instrument_id: int) -> set[int]:
        res = await self.session.execute(
            select(IndexMembership.constituent_instrument_id).where(
                IndexMembership.index_instrument_id == index_instrument_id,
                IndexMembership.effective_to.is_(None),
            )
        )
        return set(res.scalars())

    async def add(
        self,
        index_instrument_id: int,
        constituent_instrument_id: int,
        weight: Decimal | None = None,
    ) -> None:
        self.session.add(
            IndexMembership(
                index_instrument_id=index_instrument_id,
                constituent_instrument_id=constituent_instrument_id,
                weight=weight,
            )
        )

    async def close(
        self,
        index_instrument_id: int,
        constituent_instrument_id: int,
        effective_to: dt.date,
    ) -> None:
        await self.session.execute(
            update(IndexMembership)
            .where(
                IndexMembership.index_instrument_id == index_instrument_id,
                IndexMembership.constituent_instrument_id == constituent_instrument_id,
                IndexMembership.effective_to.is_(None),
            )
            .values(effective_to=effective_to)
        )

    async def constituent_instrument_ids(self, index_symbol: str) -> list[int]:
        """Currently-active constituent instrument ids for an index symbol."""
        idx = select(Instrument.id).where(Instrument.symbol == index_symbol).scalar_subquery()
        res = await self.session.execute(
            select(IndexMembership.constituent_instrument_id).where(
                and_(
                    IndexMembership.index_instrument_id == idx,
                    IndexMembership.effective_to.is_(None),
                )
            )
        )
        return list(res.scalars())
