"""Data access for incremental sync bookmarks."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Timeframe
from app.models.sync_state import DataSyncState


class SyncStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_last_synced(
        self, instrument_id: int, tf: Timeframe
    ) -> dt.datetime | None:
        res = await self.session.execute(
            select(DataSyncState.last_synced_ts).where(
                DataSyncState.instrument_id == instrument_id, DataSyncState.tf == tf
            )
        )
        return res.scalar_one_or_none()

    async def set_last_synced(
        self, instrument_id: int, tf: Timeframe, ts: dt.datetime
    ) -> None:
        stmt = insert(DataSyncState).values(
            instrument_id=instrument_id, tf=tf, last_synced_ts=ts
        )
        stmt = stmt.on_conflict_do_update(
            constraint="pk_data_sync_state",
            set_={"last_synced_ts": stmt.excluded.last_synced_ts, "updated_at": dt.datetime.now(dt.timezone.utc)},
        )
        await self.session.execute(stmt)
