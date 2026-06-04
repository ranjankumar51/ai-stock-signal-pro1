"""Scoring-dimension primitives (Strategy pattern, mirroring indicators).

Each fusion input is one Dimension produced by a ScoreProvider. A provider
returns a DimensionScore: a normalized directional score in [-1, 1], a
confidence in [0, 1], and an ``available`` flag. Unavailable dimensions (the
Phase 3 fundamental/news/social/volatility placeholders) are excluded from the
fuse exactly like an insufficient indicator is excluded from the technical
composite. Providers read time only from ``ctx.as_of`` (clock-driven), so the
whole layer is point-in-time correct and mode-agnostic.
"""
from __future__ import annotations

import datetime as dt
import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid importing DB-coupled enums at module load
    from app.models.enums import Timeframe


class Dimension(str, enum.Enum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    NEWS = "news"
    SOCIAL = "social"
    VOLATILITY = "volatility"


@dataclass(slots=True)
class DimensionScore:
    dimension: Dimension
    score: float            # [-1, 1], + = bullish
    confidence: float       # [0, 1]
    available: bool = True   # False => not-yet-implemented; excluded from fuse
    detail: dict = field(default_factory=dict)


@dataclass(slots=True)
class ProviderContext:
    instrument_id: int
    tf: "Timeframe"
    as_of: dt.datetime


class ScoreProvider(ABC):
    """Strategy producing one DimensionScore."""

    dimension: Dimension

    @abstractmethod
    async def score(self, ctx: ProviderContext) -> DimensionScore: ...

    def _unavailable(self, reason: str = "not_implemented") -> DimensionScore:
        return DimensionScore(
            self.dimension, 0.0, 0.0, available=False, detail={"reason": reason}
        )
