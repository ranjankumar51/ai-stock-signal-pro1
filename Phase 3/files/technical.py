"""Technical dimension provider — reuses the Phase 2 engine unchanged.

Runs the point-in-time TechnicalAnalysisEngine (bounded to ctx.as_of via the
injected Clock/DataFeed) and adapts its TechnicalResult into a DimensionScore.
The full technical breakdown is carried in ``detail`` so the pipeline can also
persist the analysis_snapshots row without recomputing.
"""
from __future__ import annotations

from app.analysis.technical.engine import TechnicalAnalysisEngine
from app.fusion.dimensions import (
    Dimension,
    DimensionScore,
    ProviderContext,
    ScoreProvider,
)


class TechnicalScoreProvider(ScoreProvider):
    dimension = Dimension.TECHNICAL

    def __init__(self, engine: TechnicalAnalysisEngine) -> None:
        self.engine = engine

    async def score(self, ctx: ProviderContext) -> DimensionScore:
        res = await self.engine.analyze(ctx.instrument_id, ctx.tf)
        return DimensionScore(
            self.dimension,
            score=res.score,
            confidence=res.confidence,
            available=not res.insufficient,
            detail=res.to_details(ctx.tf.value),
        )
