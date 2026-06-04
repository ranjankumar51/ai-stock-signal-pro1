"""Volume analysis — relative volume confirming the latest price move.

Direction comes from the last price change; magnitude from how far the latest
volume exceeds its recent average (volume confirms moves).
"""
from __future__ import annotations

import numpy as np

from app.analysis.technical import calc
from app.analysis.technical.base import Indicator, IndicatorResult, clip, squash
from app.analysis.technical.series import OHLCVSeries


class VolumeIndicator(Indicator):
    name = "volume"

    def __init__(self, period: int = 20) -> None:
        self.period = period

    @property
    def lookback(self) -> int:
        return self.period * 2

    def compute(self, s: OHLCVSeries) -> IndicatorResult:
        if len(s) < self.period + 1:
            return self._insufficient()
        avg_vol = float(calc.sma(s.volume, self.period)[-1])
        last_vol = float(s.volume[-1])
        rel = last_vol / (avg_vol + calc.EPS)
        price_dir = float(np.sign(s.close[-1] - s.close[-2]))
        score = clip(price_dir * squash(rel - 1.0, k=1.0))
        confidence = clip(0.3 + min(0.6, abs(rel - 1.0) * 0.5), 0.0, 1.0)
        return IndicatorResult(
            self.name,
            {"rel_volume": rel, "avg_volume": avg_vol, "last_volume": last_vol},
            score,
            confidence,
            {"high_volume": rel >= 1.5},
        )
