"""Relative Strength Index (Wilder)."""
from __future__ import annotations

import numpy as np

from app.analysis.technical import calc
from app.analysis.technical.base import Indicator, IndicatorResult, clip
from app.analysis.technical.series import OHLCVSeries


class RSIIndicator(Indicator):
    name = "rsi"

    def __init__(self, period: int = 14) -> None:
        self.period = period

    @property
    def lookback(self) -> int:
        return self.period * 5

    def compute(self, s: OHLCVSeries) -> IndicatorResult:
        if len(s) < self.period + 1:
            return self._insufficient()
        delta = np.diff(s.close)
        gains = np.where(delta > 0, delta, 0.0)
        losses = np.where(delta < 0, -delta, 0.0)
        avg_gain = calc.rma(gains, self.period)[-1]
        avg_loss = calc.rma(losses, self.period)[-1]
        rs = avg_gain / (avg_loss + calc.EPS)
        rsi = 100.0 - 100.0 / (1.0 + rs)

        score = clip((rsi - 50.0) / 50.0)
        confidence = clip(0.3 + abs(rsi - 50.0) / 50.0 * 0.7, 0.0, 1.0)
        meta = {"overbought": rsi >= 70, "oversold": rsi <= 30}
        return IndicatorResult(self.name, {"rsi": float(rsi)}, score, confidence, meta)
