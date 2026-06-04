"""MACD (12, 26, 9)."""
from __future__ import annotations

from app.analysis.technical import calc
from app.analysis.technical.base import Indicator, IndicatorResult, clip, squash
from app.analysis.technical.series import OHLCVSeries


class MACDIndicator(Indicator):
    name = "macd"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9) -> None:
        self.fast, self.slow, self.signal = fast, slow, signal

    @property
    def lookback(self) -> int:
        return (self.slow + self.signal) * 4

    def compute(self, s: OHLCVSeries) -> IndicatorResult:
        if len(s) < self.slow + self.signal:
            return self._insufficient()
        macd_line = calc.ema(s.close, self.fast) - calc.ema(s.close, self.slow)
        signal_line = calc.ema(macd_line, self.signal)
        hist = macd_line - signal_line

        close = s.close[-1]
        norm_hist = float(hist[-1]) / (close + calc.EPS)
        score = squash(norm_hist, k=200.0)
        confidence = clip(0.4 + min(0.6, abs(norm_hist) * 120.0), 0.0, 1.0)
        values = {
            "macd": float(macd_line[-1]),
            "signal": float(signal_line[-1]),
            "hist": float(hist[-1]),
        }
        meta = {"bullish_cross": macd_line[-1] > signal_line[-1]}
        return IndicatorResult(self.name, values, score, confidence, meta)
