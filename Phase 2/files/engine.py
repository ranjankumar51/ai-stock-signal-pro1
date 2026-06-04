"""Technical analysis engine.

Mode-agnostic: it reads candles only through the injected DataFeed (bounded to
clock.now()), so the identical engine runs live or in backtest replay. It does
not generate signals — only indicator values, trend, score, and confidence.

Performance:
  * fetches only ``max(indicator.lookback)`` candles, not full history;
  * builds the numpy series once and shares it across indicators;
  * each indicator is O(window).
"""
from __future__ import annotations

from app.analysis.technical.base import Indicator
from app.analysis.technical.indicators import DEFAULT_WEIGHTS, default_indicators
from app.analysis.technical.scoring import (
    ScoredItem,
    TechnicalResult,
    TechnicalScoringEngine,
)
from app.analysis.technical.series import OHLCVSeries
from app.core.logging import get_logger
from app.models.enums import Timeframe
from app.runtime.clock import Clock
from app.runtime.datafeed import DataFeed

log = get_logger(__name__)


class TechnicalAnalysisEngine:
    def __init__(
        self,
        datafeed: DataFeed,
        clock: Clock,
        indicators: list[Indicator] | None = None,
        weights: dict[str, float] | None = None,
        lookback_buffer: int = 10,
    ) -> None:
        self.feed = datafeed
        self.clock = clock
        self.indicators = indicators or default_indicators()
        self.weights = weights or DEFAULT_WEIGHTS
        self.scoring = TechnicalScoringEngine()
        self._fetch_limit = max(i.lookback for i in self.indicators) + lookback_buffer

    async def analyze(self, instrument_id: int, tf: Timeframe) -> TechnicalResult:
        as_of = self.clock.now()
        candles = await self.feed.get_candles(
            instrument_id, tf, end=as_of, limit=self._fetch_limit
        )
        series = OHLCVSeries.from_candles(candles)

        items: list[ScoredItem] = []
        indicator_detail: dict = {}
        for ind in self.indicators:
            try:
                r = ind.compute(series)
            except Exception as exc:  # noqa: BLE001 - one bad indicator shouldn't fail all
                log.warning("indicator.error", indicator=ind.name, error=str(exc))
                r = ind._insufficient()
            items.append(
                ScoredItem(
                    name=ind.name,
                    score=r.score,
                    confidence=r.confidence,
                    directional=ind.directional,
                    weight=self.weights.get(ind.name, 1.0),
                    insufficient=r.insufficient,
                )
            )
            indicator_detail[ind.name] = {
                "values": r.values,
                "score": round(r.score, 4),
                "confidence": round(r.confidence, 4),
                "directional": ind.directional,
                "insufficient": r.insufficient,
                "meta": r.meta,
            }

        result = self.scoring.aggregate(items, as_of=as_of, n_candles=len(series))
        result.indicators = indicator_detail
        return result
