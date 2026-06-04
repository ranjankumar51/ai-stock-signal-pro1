"""Data access for analysis_snapshots."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ExecutionMode, Timeframe
from app.models.scoring import AnalysisSnapshot


class SnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        *,
        instrument_id: int,
        tf: Timeframe,
        ts: dt.datetime,
        tech_score: Decimal | None = None,
        details: dict | None = None,
        mode: ExecutionMode = ExecutionMode.LIVE,
        backtest_run_id: int | None = None,
    ) -> None:
        """Insert or update the snapshot for (instrument, tf, ts).

        Only the technical fields are written in Phase 2; the other dimension
        scores remain NULL until their engines exist.
        """
        stmt = insert(AnalysisSnapshot).values(
            instrument_id=instrument_id,
            tf=tf,
            ts=ts,
            tech_score=tech_score,
            details=details,
            mode=mode,
            backtest_run_id=backtest_run_id,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_analysis_snapshots_instrument_id_tf_ts",
            set_={
                "tech_score": stmt.excluded.tech_score,
                "details": stmt.excluded.details,
                "mode": stmt.excluded.mode,
                "backtest_run_id": stmt.excluded.backtest_run_id,
            },
        )
        await self.session.execute(stmt)
