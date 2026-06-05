"""Data access for generated signals (idempotent point-in-time upsert)."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ExecutionMode, SignalStatus, SignalType, Timeframe, TradeSide
from app.models.scoring import Signal


class SignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        *,
        instrument_id: int,
        tf: Timeframe,
        ts: dt.datetime,
        signal: SignalType,
        composite_score: Decimal,
        confidence: Decimal,
        status: SignalStatus,
        side: TradeSide | None = None,
        # --- risk plan (Phase 4) ---
        entry: Decimal | None = None,
        stop_loss: Decimal | None = None,
        target: Decimal | None = None,
        risk_reward: Decimal | None = None,
        position_size: Decimal | None = None,
        risk_confidence: Decimal | None = None,
        snapshot_id: int | None = None,
        weights_version_id: int | None = None,
        rationale: dict | None = None,
        mode: ExecutionMode = ExecutionMode.LIVE,
        backtest_run_id: int | None = None,
    ) -> int:
        """Insert or update the signal for the point-in-time natural key
        (instrument, tf, ts, mode, backtest_run_id). Re-running generation for
        the same instant is therefore idempotent — required for clean backtest
        replay. ``isnot_distinct_from`` makes the NULL backtest_run_id (LIVE)
        case match correctly.
        """
        existing = (
            await self.session.execute(
                select(Signal).where(
                    Signal.instrument_id == instrument_id,
                    Signal.tf == tf,
                    Signal.ts == ts,
                    Signal.mode == mode,
                    Signal.backtest_run_id.isnot_distinct_from(backtest_run_id),
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            row = Signal(
                instrument_id=instrument_id,
                tf=tf,
                ts=ts,
                signal=signal,
                composite_score=composite_score,
                confidence=confidence,
                side=side,
                entry=entry,
                stop_loss=stop_loss,
                target=target,
                risk_reward=risk_reward,
                position_size=position_size,
                risk_confidence=risk_confidence,
                status=status,
                snapshot_id=snapshot_id,
                weights_version_id=weights_version_id,
                rationale=rationale,
                mode=mode,
                backtest_run_id=backtest_run_id,
            )
            self.session.add(row)
            await self.session.flush()
            return row.id

        existing.signal = signal
        existing.composite_score = composite_score
        existing.confidence = confidence
        existing.side = side
        existing.entry = entry
        existing.stop_loss = stop_loss
        existing.target = target
        existing.risk_reward = risk_reward
        existing.position_size = position_size
        existing.risk_confidence = risk_confidence
        existing.status = status
        existing.snapshot_id = snapshot_id
        existing.weights_version_id = weights_version_id
        existing.rationale = rationale
        await self.session.flush()
        return existing.id

    async def get_latest(
        self,
        instrument_id: int,
        tf: Timeframe,
        mode: ExecutionMode = ExecutionMode.LIVE,
    ) -> Signal | None:
        res = await self.session.execute(
            select(Signal)
            .where(
                Signal.instrument_id == instrument_id,
                Signal.tf == tf,
                Signal.mode == mode,
            )
            .order_by(Signal.ts.desc())
            .limit(1)
        )
        return res.scalar_one_or_none()
