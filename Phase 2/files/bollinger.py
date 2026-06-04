"""Bollinger Bands (20, 2)."""
from __future__ import annotations

from app.analysis.technical import calc
from app.analysis.technical.base import Indicator, IndicatorResult, clip
from app.analysis.technical.series import OHLCVSeries


class BollingerIndicator(Indicator):
    name = "bollinger"

    def __init__(self, period: int = 20, num_std: float = 2.0) -> None:
        self.period = period
        self.num_std = num_std

    @property
    def lookback(self) -> int:
        return self.period * 3

    def compute(self, s: OHLCVSeries) -> IndicatorResult:
        if len(s) < self.period:
            return self._insufficient()
        mid = float(calc.sma(s.close, self.period)[-1])
        sd = float(calc.rolling_std(s.close, self.period, ddof=0)[-1])
        upper = mid + self.num_std * sd
        lower = mid - self.num_std * sd
        close = float(s.close[-1])

        width = upper - lower
        pct_b = (close - lower) / (width + calc.EPS)
        score = clip((close - mid) / (self.num_std * sd + calc.EPS))
        bandwidth = width / (mid + calc.EPS)
        confidence = clip(0.4 + min(0.5, abs(score) * 0.5), 0.0, 1.0)
        values = {
            "mid": mid,
            "upper": upper,
            "lower": lower,
            "pct_b": pct_b,
            "bandwidth": bandwidth,
        }
        return IndicatorResult(self.name, values, score, confidence, {})
