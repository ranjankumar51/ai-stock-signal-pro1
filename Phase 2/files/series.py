"""Immutable OHLCV series fed to indicators.

Built once per analysis from a bounded candle window and reused across all
indicators, so array allocation/conversion happens a single time.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np

from app.ingestion.dto import Candle


@dataclass(slots=True)
class OHLCVSeries:
    ts: list[dt.datetime]
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray

    def __len__(self) -> int:
        return len(self.ts)

    @classmethod
    def from_candles(cls, candles: list[Candle]) -> "OHLCVSeries":
        ordered = sorted(candles, key=lambda c: c.ts)
        return cls(
            ts=[c.ts for c in ordered],
            open=np.array([float(c.open) for c in ordered], dtype=np.float64),
            high=np.array([float(c.high) for c in ordered], dtype=np.float64),
            low=np.array([float(c.low) for c in ordered], dtype=np.float64),
            close=np.array([float(c.close) for c in ordered], dtype=np.float64),
            volume=np.array([float(c.volume) for c in ordered], dtype=np.float64),
        )
