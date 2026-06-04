"""Technical analysis service.

Thin orchestration: wire a Clock + DbDataFeed + engine, run the analysis, and
persist the result into analysis_snapshots (normalized score in ``tech_score``,
the full breakdown incl. the 0-100 score in ``details``). Works in both modes —
pass a SimulatedClock + BACKTEST mode for historical replay.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.technical.engine import TechnicalAnalysisEngine
from app.analysis.technical.scoring import TechnicalResult
from app.core.logging import get_logger
from app.models.enums import ExecutionMode, Timeframe
from app.repositories.snapshot_repo import SnapshotRepository
from app.runtime.clock import Clock, LiveClock
from app.runtime.datafeed import DbDataFeed

log = get_logger(__name__)


class TechnicalAnalysisService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None) -> None:
        self.session = session
        self.clock = clock or LiveClock()
        self.engine = TechnicalAnalysisEngine(DbDataFeed(session, self.clock), self.clock)
        self.snapshots = SnapshotRepository(session)

    async def analyze(self, instrument_id: int, tf: Timeframe) -> TechnicalResult:
        return await self.engine.analyze(instrument_id, tf)

    async def analyze_and_store(
        self,
        instrument_id: int,
        tf: Timeframe,
        mode: ExecutionMode = ExecutionMode.LIVE,
        backtest_run_id: int | None = None,
    ) -> TechnicalResult:
        result = await self.engine.analyze(instrument_id, tf)
        tech_score = None if result.insufficient else Decimal(str(round(result.score, 4)))
        await self.snapshots.upsert(
            instrument_id=instrument_id,
            tf=tf,
            ts=result.as_of,
            tech_score=tech_score,
            details=result.to_details(tf.value),
            mode=mode,
            backtest_run_id=backtest_run_id,
        )
        await self.session.commit()
        log.info(
            "technical.analyzed",
            instrument_id=instrument_id,
            tf=tf.value,
            trend=result.trend,
            score_0_100=result.score_0_100,
            confidence=round(result.confidence, 3),
        )
        return result
