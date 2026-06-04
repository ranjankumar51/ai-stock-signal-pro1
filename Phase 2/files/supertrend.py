"""SuperTrend (period 10, multiplier 3) using Wilder ATR.

Stateful band-flip algorithm; computed iteratively over the bounded window.
"""
from __future__ import annotations

import numpy as np

from app.analysis.technical import calc
from app.analysis.technical.base import Indicator, IndicatorResult, clip
from app.analysis.technical.series import OHLCVSeries


class SuperTrendIndicator(Indicator):
    name = "supertrend"

    def __init__(self, period: int = 10, multiplier: float = 3.0) -> None:
        self.period = period
        self.multiplier = multiplier

    @property
    def lookback(self) -> int:
        return self.period * 5

    def compute(self, s: OHLCVSeries) -> IndicatorResult:
        n = len(s)
        if n < self.period + 1:
            return self._insufficient()
        high, low, close = s.high, s.low, s.close
        tr = calc.true_range(high, low, close)
        atr = calc.rma(tr, self.period)
        hl2 = (high + low) / 2.0
        upper = hl2 + self.multiplier * atr
        lower = hl2 - self.multiplier * atr

        final_upper = np.copy(upper)
        final_lower = np.copy(lower)
        direction = np.ones(n, dtype=np.int8)  # 1 up, -1 down
        start = self.period
        for i in range(start + 1, n):
            final_upper[i] = (
                min(upper[i], final_upper[i - 1])
                if close[i - 1] <= final_upper[i - 1]
                else upper[i]
            )
            final_lower[i] = (
                max(lower[i], final_lower[i - 1])
                if close[i - 1] >= final_lower[i - 1]
                else lower[i]
            )
            if close[i] > final_upper[i - 1]:
                direction[i] = 1
            elif close[i] < final_lower[i - 1]:
                direction[i] = -1
            else:
                direction[i] = direction[i - 1]

        d = int(direction[-1])
        st_line = float(final_lower[-1] if d == 1 else final_upper[-1])
        atr_v = float(atr[-1])
        dist = abs(float(close[-1]) - st_line) / (self.multiplier * atr_v + calc.EPS)
        score = clip(d * min(1.0, dist))
        confidence = clip(0.5 + 0.5 * min(1.0, dist), 0.0, 1.0)
        return IndicatorResult(
            self.name,
            {"supertrend": st_line, "direction": float(d)},
            score,
            confidence,
            {"uptrend": d == 1},
        )
