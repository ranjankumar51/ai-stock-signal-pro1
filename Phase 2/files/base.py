"""Indicator strategy interface.

Each indicator is an interchangeable strategy: it takes an OHLCVSeries and
returns an IndicatorResult carrying its raw values plus a normalized
directional read (score in [-1, 1]) and a confidence in [0, 1]. Non-directional
indicators (e.g. ATR) set ``directional = False`` and are excluded from the
directional composite but still reported.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

from app.analysis.technical.series import OHLCVSeries


@dataclass(slots=True)
class IndicatorResult:
    name: str
    values: dict[str, float]
    score: float  # [-1, 1], + = bullish
    confidence: float  # [0, 1]
    meta: dict = field(default_factory=dict)
    insufficient: bool = False


class Indicator(ABC):
    name: str = "abstract"
    directional: bool = True

    @property
    @abstractmethod
    def lookback(self) -> int:
        """Minimum candles required for a meaningful value."""

    @abstractmethod
    def compute(self, s: OHLCVSeries) -> IndicatorResult:
        ...

    def _insufficient(self) -> IndicatorResult:
        return IndicatorResult(
            self.name, {}, 0.0, 0.0, {"reason": "insufficient_data"}, insufficient=True
        )


def squash(x: float, k: float = 1.0) -> float:
    """Bounded squashing into (-1, 1)."""
    return float(np.tanh(k * x))


def clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return float(min(hi, max(lo, x)))
