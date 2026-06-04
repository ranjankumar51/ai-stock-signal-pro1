"""Volume-Weighted Average Price, anchored to the latest IST trading session.

VWAP is an intraday measure; it resets each session. For daily candles the
session degenerates to a single bar and the score is ~neutral (documented).
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

import numpy as np

from app.analysis.technical import calc
from app.analysis.technical.base import Indicator, IndicatorResult, clip, squash
from app.analysis.technical.series import OHLCVSeries

IST = ZoneInfo("Asia/Kolkata")


class VWAPIndicator(Indicator):
    name = "vwap"

    @property
    def lookback(self) -> int:
        return 30

    def compute(self, s: OHLCVSeries) -> IndicatorResult:
        if len(s) < 1:
            return self._insufficient()
        dates = [t.astimezone(IST).date() for t in s.ts]
        last_date = dates[-1]
        mask = np.array([d == last_date for d in dates], dtype=bool)

        typical = (s.high + s.low + s.close) / 3.0
        vol = s.volume[mask]
        tp = typical[mask]
        denom = float(vol.sum())
        vwap = float((tp * vol).sum() / denom) if denom > 0 else float(tp.mean())

        close = float(s.close[-1])
        dev = (close - vwap) / (vwap + calc.EPS)
        score = squash(dev, k=20.0)
        confidence = clip(0.3 + min(0.6, abs(dev) * 30.0), 0.0, 1.0)
        return IndicatorResult(
            self.name,
            {"vwap": vwap, "price_vs_vwap_pct": dev * 100.0},
            score,
            confidence,
            {"session_bars": int(mask.sum())},
        )
