"""Exponential Moving Average — price vs EMA read.

Instantiated per period (20/50/200). Score reflects how far price sits above
(bullish) or below (bearish) the EMA, squashed to [-1, 1].
"""
from __future__ import annotations

from app.analysis.technical import calc
from app.analysis.technical.base import Indicator, IndicatorResult, clip, squash
from app.analysis.technical.series import OHLCVSeries


class EMAIndicator(Indicator):
    def __init__(self, period: int) -> None:
        self.period = period
        self.name = f"ema{period}"

    @property
    def lookback(self) -> int:
        return self.period * 5

    def compute(self, s: OHLCVSeries) -> IndicatorResult:
        if len(s) < self.period:
            return self._insufficient()
        ema_val = float(calc.ema(s.close, self.period)[-1])
        close = float(s.close[-1])
        dev = (close - ema_val) / (ema_val + calc.EPS)
        score = squash(dev, k=20.0)
        confidence = clip(0.4 + min(0.6, abs(dev) * 30.0), 0.0, 1.0)
        return IndicatorResult(
            self.name,
            {self.name: ema_val, "price_vs_ema_pct": dev * 100.0},
            score,
            confidence,
            {"above": close > ema_val},
        )
