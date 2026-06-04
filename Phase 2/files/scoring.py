"""Technical scoring engine.

Fuses per-indicator directional reads into:
  * a normalized composite score in [-1, 1] (stored in analysis_snapshots),
  * a composite technical score in [0, 100] (presentation),
  * a trend label,
  * a confidence in [0, 1] blending data sufficiency, indicator agreement, and
    average per-indicator confidence.
No buy/sell or risk logic — direction, score, trend, confidence only.
"""
from __future__ import annotations

import datetime as dt
import enum
from dataclasses import dataclass, field

import numpy as np


class TechnicalTrend(str, enum.Enum):
    STRONG_BEARISH = "STRONG_BEARISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    BULLISH = "BULLISH"
    STRONG_BULLISH = "STRONG_BULLISH"


@dataclass(slots=True)
class ScoredItem:
    name: str
    score: float
    confidence: float
    directional: bool
    weight: float
    insufficient: bool


@dataclass(slots=True)
class TechnicalResult:
    as_of: dt.datetime
    score: float          # normalized [-1, 1]
    score_0_100: float    # presentation [0, 100]
    trend: str
    confidence: float     # [0, 1]
    n_candles: int
    insufficient: bool
    indicators: dict = field(default_factory=dict)

    def to_details(self, tf: str) -> dict:
        return {
            "score_0_100": self.score_0_100,
            "score_norm": round(self.score, 4),
            "trend": self.trend,
            "confidence": round(self.confidence, 4),
            "tf": tf,
            "n_candles": self.n_candles,
            "insufficient": self.insufficient,
            "as_of": self.as_of.isoformat(),
            "indicators": self.indicators,
        }


def _trend(score_0_100: float) -> TechnicalTrend:
    if score_0_100 >= 75:
        return TechnicalTrend.STRONG_BULLISH
    if score_0_100 >= 58:
        return TechnicalTrend.BULLISH
    if score_0_100 > 42:
        return TechnicalTrend.NEUTRAL
    if score_0_100 > 25:
        return TechnicalTrend.BEARISH
    return TechnicalTrend.STRONG_BEARISH


class TechnicalScoringEngine:
    def aggregate(
        self, items: list[ScoredItem], as_of: dt.datetime, n_candles: int
    ) -> TechnicalResult:
        directional = [i for i in items if i.directional]
        valid = [i for i in directional if not i.insufficient and i.weight > 0]

        if not valid:
            return TechnicalResult(
                as_of=as_of, score=0.0, score_0_100=50.0,
                trend=TechnicalTrend.NEUTRAL.value, confidence=0.0,
                n_candles=n_candles, insufficient=True,
            )

        weights = np.array([i.weight for i in valid], dtype=np.float64)
        scores = np.array([i.score for i in valid], dtype=np.float64)
        confs = np.array([i.confidence for i in valid], dtype=np.float64)

        composite = float(np.sum(weights * scores) / np.sum(weights))
        composite = max(-1.0, min(1.0, composite))
        score_0_100 = round((composite + 1.0) * 50.0, 2)

        data_sufficiency = len(valid) / max(1, len(directional))
        agreement = 1.0 - min(1.0, float(np.std(scores)))
        avg_conf = float(np.mean(confs))
        confidence = max(
            0.0,
            min(1.0, 0.4 * data_sufficiency + 0.3 * agreement + 0.3 * avg_conf),
        )

        return TechnicalResult(
            as_of=as_of,
            score=composite,
            score_0_100=score_0_100,
            trend=_trend(score_0_100).value,
            confidence=confidence,
            n_candles=n_candles,
            insufficient=False,
        )
