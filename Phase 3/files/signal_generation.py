"""Analysis-to-signal pipeline (orchestration only).

Wires the existing Phase 2 runtime (Clock + DataFeed + TechnicalAnalysisEngine)
to the Phase 3 fusion + classification layers and persists the result. Works in
both modes — pass a SimulatedClock + ExecutionMode.BACKTEST + backtest_run_id
for historical replay. All time access goes through the clock, so point-in-time
correctness and the no-look-ahead guarantee are inherited unchanged.

Flow per (instrument, tf):
    providers -> DimensionScores -> persist technical snapshot
    -> FusionScoringEngine -> SignalClassifier -> persist Signal
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.technical.engine import TechnicalAnalysisEngine
from app.core.logging import get_logger
from app.fusion.classifier import Classification, SignalClassifier
from app.fusion.dimensions import Dimension, DimensionScore, ProviderContext, ScoreProvider
from app.fusion.fusion_engine import FusionResult, FusionScoringEngine
from app.fusion.providers import DEFAULT_FUSION_WEIGHTS, default_providers
from app.fusion.providers.technical import TechnicalScoreProvider
from app.models.enums import ExecutionMode, Timeframe
from app.repositories.signal_repo import SignalRepository
from app.repositories.snapshot_repo import SnapshotRepository
from app.repositories.weights_repo import WeightsRepository
from app.runtime.clock import Clock, LiveClock
from app.runtime.datafeed import DbDataFeed

log = get_logger(__name__)


@dataclass(slots=True)
class GeneratedSignal:
    signal_id: int
    snapshot_id: int | None
    instrument_id: int
    tf: Timeframe
    as_of: dt.datetime
    classification: Classification
    fusion: FusionResult
    mode: ExecutionMode
    backtest_run_id: int | None


class SignalGenerationService:
    def __init__(
        self,
        session: AsyncSession | None,
        clock: Clock | None = None,
        *,
        providers: list[ScoreProvider] | None = None,
        fusion: FusionScoringEngine | None = None,
        classifier: SignalClassifier | None = None,
        weights: dict[str, float] | None = None,
        weights_repo: WeightsRepository | None = None,
        snapshot_repo: SnapshotRepository | None = None,
        signal_repo: SignalRepository | None = None,
    ) -> None:
        self.session = session
        self.clock = clock or LiveClock()
        if providers is None:
            engine = TechnicalAnalysisEngine(DbDataFeed(session, self.clock), self.clock)
            providers = default_providers(TechnicalScoreProvider(engine))
        self.providers = providers
        self.fusion = fusion or FusionScoringEngine()
        self.classifier = classifier or SignalClassifier()
        self._weights_override = weights
        self.weights_repo = weights_repo or (WeightsRepository(session) if session else None)
        self.snapshots = snapshot_repo or (SnapshotRepository(session) if session else None)
        self.signals = signal_repo or (SignalRepository(session) if session else None)

    async def _resolve_weights(self) -> tuple[dict[str, float], int | None, int | None]:
        if self._weights_override is not None:
            return self._weights_override, None, None
        if self.weights_repo is not None:
            row = await self.weights_repo.get_active()
            if row is not None:
                return dict(row.weights), row.version, row.id
        return DEFAULT_FUSION_WEIGHTS, None, None

    async def generate(
        self,
        instrument_id: int,
        tf: Timeframe,
        *,
        mode: ExecutionMode = ExecutionMode.LIVE,
        backtest_run_id: int | None = None,
    ) -> GeneratedSignal:
        as_of = self.clock.now()
        ctx = ProviderContext(instrument_id=instrument_id, tf=tf, as_of=as_of)

        scores: list[DimensionScore] = [await p.score(ctx) for p in self.providers]
        tech = next(s for s in scores if s.dimension is Dimension.TECHNICAL)

        snapshot_id: int | None = None
        if self.snapshots is not None:
            tech_score = (
                Decimal(str(tech.detail.get("score_norm")))
                if tech.available and tech.detail.get("score_norm") is not None
                else None
            )
            snapshot_id = await self.snapshots.upsert(
                instrument_id=instrument_id,
                tf=tf,
                ts=as_of,
                tech_score=tech_score,
                details=tech.detail,
                mode=mode,
                backtest_run_id=backtest_run_id,
            )

        weights, version, version_id = await self._resolve_weights()
        fr = self.fusion.aggregate(scores, weights, as_of, weights_version=version)
        cls = self.classifier.classify(fr.composite, fr.confidence)

        signal_id = -1
        if self.signals is not None:
            signal_id = await self.signals.upsert(
                instrument_id=instrument_id,
                tf=tf,
                ts=as_of,
                signal=cls.signal,
                composite_score=Decimal(str(round(fr.composite, 4))),
                confidence=Decimal(str(round(fr.confidence, 4))),
                side=cls.side,
                status=cls.status,
                snapshot_id=snapshot_id,
                weights_version_id=version_id,
                rationale=fr.to_rationale(tf.value),
                mode=mode,
                backtest_run_id=backtest_run_id,
            )

        if self.session is not None:
            await self.session.commit()

        log.info(
            "signal.generated",
            instrument_id=instrument_id,
            tf=tf.value,
            mode=mode.value,
            signal=cls.signal.value,
            composite=round(fr.composite, 4),
            confidence=round(fr.confidence, 3),
            weights_version=version,
        )
        return GeneratedSignal(
            signal_id=signal_id,
            snapshot_id=snapshot_id,
            instrument_id=instrument_id,
            tf=tf,
            as_of=as_of,
            classification=cls,
            fusion=fr,
            mode=mode,
            backtest_run_id=backtest_run_id,
        )
