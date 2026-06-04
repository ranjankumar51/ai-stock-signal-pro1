"""Average True Range (Wilder). Volatility, not direction.

Directional flag is False, so ATR is excluded from the directional composite. It
is still reported (and feeds the volatility context for later phases)."""
from __future__ import annotations

from app.analysis.technical import calc
from app.analysis.technical.base import Indicator, IndicatorResult
from app.analysis.technical.series import OHLCVSeries


class ATRIndicator(Indicator):
    name = "atr"
    directional = False

    def __init__(self, period: int = 14) -> None:
        self.period = period

    @property
    def lookback(self) -> int:
        return self.period * 5

    def compute(self, s: OHLCVSeries) -> IndicatorResult:
        if len(s) < self.period + 1:
            return self._insufficient()
        tr = calc.true_range(s.high, s.low, s.close)
        atr = float(calc.rma(tr, self.period)[-1])
        close = float(s.close[-1])
        atr_pct = atr / (close + calc.EPS) * 100.0
        return IndicatorResult(
            self.name,
            {"atr": atr, "atr_pct": atr_pct},
            score=0.0,  # non-directional
            confidence=1.0,
            meta={"volatility_pct": atr_pct},
        )
