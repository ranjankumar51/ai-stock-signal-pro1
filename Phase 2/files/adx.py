"""Average Directional Index with directional indicators (+DI / -DI).

ADX measures trend strength; the sign of (+DI − −DI) gives direction. Score is
direction scaled by strength; confidence rises with ADX.
"""
from __future__ import annotations

import numpy as np

from app.analysis.technical import calc
from app.analysis.technical.base import Indicator, IndicatorResult, clip
from app.analysis.technical.series import OHLCVSeries


class ADXIndicator(Indicator):
    name = "adx"

    def __init__(self, period: int = 14) -> None:
        self.period = period

    @property
    def lookback(self) -> int:
        return self.period * 6

    def compute(self, s: OHLCVSeries) -> IndicatorResult:
        if len(s) < self.period * 2 + 1:
            return self._insufficient()
        high, low, close = s.high, s.low, s.close
        up = high[1:] - high[:-1]
        down = low[:-1] - low[1:]
        plus_dm = np.where((up > down) & (up > 0), up, 0.0)
        minus_dm = np.where((down > up) & (down > 0), down, 0.0)
        tr = calc.true_range(high, low, close)[1:]

        atr = calc.rma(tr, self.period)
        plus_di = 100.0 * calc.rma(plus_dm, self.period) / (atr + calc.EPS)
        minus_di = 100.0 * calc.rma(minus_dm, self.period) / (atr + calc.EPS)
        dx = 100.0 * np.abs(plus_di - minus_di) / (plus_di + minus_di + calc.EPS)
        # +DI/-DI are valid from index (period-1); seed the ADX smoothing on the
        # first valid dx window so leading NaNs don't poison Wilder's seed.
        first = self.period - 1
        adx = calc.rma(dx[first:], self.period)

        adx_v = float(adx[-1])
        pdi, mdi = float(plus_di[-1]), float(minus_di[-1])
        direction = (pdi - mdi) / (pdi + mdi + calc.EPS)
        strength = min(1.0, adx_v / 50.0)
        score = clip(direction * strength)
        confidence = clip(min(1.0, adx_v / 40.0), 0.0, 1.0)
        return IndicatorResult(
            self.name,
            {"adx": adx_v, "plus_di": pdi, "minus_di": mdi},
            score,
            confidence,
            {"trending": adx_v >= 25},
        )
