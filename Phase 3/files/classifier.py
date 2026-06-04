"""Signal classification.

Maps a fused composite (with a confidence gate) to a discrete SignalType and
trade side. Deterministic and reproducible. No risk management — entry / stop /
target are Phase 4.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import SignalStatus, SignalType, TradeSide

STRONG = 0.50          # |composite| >= STRONG -> STRONG_BUY / STRONG_SELL
WEAK = 0.15            # |composite| >= WEAK   -> BUY / SELL
MIN_CONFIDENCE = 0.20  # below this -> HOLD regardless of composite


@dataclass(slots=True)
class Classification:
    signal: SignalType
    side: TradeSide | None
    status: SignalStatus


class SignalClassifier:
    def __init__(
        self,
        strong: float = STRONG,
        weak: float = WEAK,
        min_confidence: float = MIN_CONFIDENCE,
    ) -> None:
        self.strong = strong
        self.weak = weak
        self.min_confidence = min_confidence

    def classify(self, composite: float, confidence: float) -> Classification:
        if confidence < self.min_confidence:
            return Classification(SignalType.HOLD, None, SignalStatus.ACTIVE)
        if composite >= self.strong:
            return Classification(SignalType.STRONG_BUY, TradeSide.LONG, SignalStatus.ACTIVE)
        if composite >= self.weak:
            return Classification(SignalType.BUY, TradeSide.LONG, SignalStatus.ACTIVE)
        if composite <= -self.strong:
            return Classification(SignalType.STRONG_SELL, TradeSide.SHORT, SignalStatus.ACTIVE)
        if composite <= -self.weak:
            return Classification(SignalType.SELL, TradeSide.SHORT, SignalStatus.ACTIVE)
        return Classification(SignalType.HOLD, None, SignalStatus.ACTIVE)
