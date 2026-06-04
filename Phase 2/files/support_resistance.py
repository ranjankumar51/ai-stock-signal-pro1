"""Support & Resistance from recent swing pivots.

Detects local extrema over a window, then takes the nearest swing low below
price as support and nearest swing high above price as resistance. Score
reflects where price sits in that range (near resistance = stronger/bullish
bias); falls back to rolling min/max when no pivots are found.
"""
from __future__ import annotations

import numpy as np

from app.analysis.technical import calc
from app.analysis.technical.base import Indicator, IndicatorResult, clip
from app.analysis.technical.series import OHLCVSeries


class SupportResistanceIndicator(Indicator):
    name = "support_resistance"

    def __init__(self, pivot_window: int = 5, lookback_bars: int = 120) -> None:
        self.pivot_window = pivot_window
        self.lookback_bars = lookback_bars

    @property
    def lookback(self) -> int:
        return self.pivot_window * 2 + 10

    def compute(self, s: OHLCVSeries) -> IndicatorResult:
        n = len(s)
        if n < self.pivot_window * 2 + 1:
            return self._insufficient()
        w = self.pivot_window
        lo = max(0, n - self.lookback_bars)
        high, low, close = s.high, s.low, s.close
        c = float(close[-1])

        swing_highs, swing_lows = [], []
        for i in range(lo + w, n - w):
            window_h = high[i - w : i + w + 1]
            window_l = low[i - w : i + w + 1]
            if high[i] == window_h.max():
                swing_highs.append(float(high[i]))
            if low[i] == window_l.min():
                swing_lows.append(float(low[i]))

        res_candidates = [h for h in swing_highs if h > c]
        sup_candidates = [lvl for lvl in swing_lows if lvl < c]
        resistance = min(res_candidates) if res_candidates else float(calc.rolling_max(high, w)[-1])
        support = max(sup_candidates) if sup_candidates else float(calc.rolling_min(low, w)[-1])

        rng = resistance - support
        position = (c - support) / (rng + calc.EPS) if rng > 0 else 0.5
        score = clip((position - 0.5) * 2.0)
        confidence = clip(0.3 + (0.5 if (res_candidates and sup_candidates) else 0.1), 0.0, 1.0)
        values = {
            "support": support,
            "resistance": resistance,
            "position": position,
            "dist_to_support_pct": (c - support) / (c + calc.EPS) * 100.0,
            "dist_to_resistance_pct": (resistance - c) / (c + calc.EPS) * 100.0,
        }
        return IndicatorResult(self.name, values, score, confidence, {})
