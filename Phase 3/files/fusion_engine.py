"""Fusion scoring engine.

Combines available DimensionScores into one composite using versioned,
per-dimension weights. Per docs/architecture.md the fuse is confidence-aware:

    composite = Σ(wᵢ · cᵢ · sᵢ) / Σ(wᵢ · cᵢ)     over available dimensions

so a low-confidence dimension contributes proportionally less. The result
carries the normalized composite in [-1, 1], a 0-100 presentation score, a
blended confidence, and a per-dimension contribution map for explainability.
Pure and side-effect-free.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import numpy as np

from app.fusion.dimensions import DimensionScore


@dataclass(slots=True)
class FusionResult:
    as_of: dt.datetime
    composite: float        # [-1, 1]
    score_0_100: float      # [0, 100]
    confidence: float       # [0, 1]
    insufficient: bool
    weights_version: int | None = None
    contributions: dict = field(default_factory=dict)

    def to_rationale(self, tf: str) -> dict:
        return {
            "composite": round(self.composite, 4),
            "score_0_100": self.score_0_100,
            "confidence": round(self.confidence, 4),
            "tf": tf,
            "insufficient": self.insufficient,
            "weights_version": self.weights_version,
            "as_of": self.as_of.isoformat(),
            "dimensions": self.contributions,
        }


class FusionScoringEngine:
    def aggregate(
        self,
        scores: list[DimensionScore],
        weights: dict[str, float],
        as_of: dt.datetime,
        weights_version: int | None = None,
    ) -> FusionResult:
        contributions: dict[str, dict] = {}
        active: list[tuple[DimensionScore, float]] = []
        for ds in scores:
            w = float(weights.get(ds.dimension.value, 0.0))
            contributions[ds.dimension.value] = {
                "score": round(ds.score, 4),
                "confidence": round(ds.confidence, 4),
                "weight": w,
                "available": ds.available,
            }
            if ds.available and w > 0:
                active.append((ds, w))

        if not active:
            return FusionResult(
                as_of, 0.0, 50.0, 0.0, True, weights_version, contributions
            )

        s = np.array([d.score for d, _ in active], dtype=np.float64)
        c = np.array([d.confidence for d, _ in active], dtype=np.float64)
        w = np.array([wt for _, wt in active], dtype=np.float64)

        denom = float(np.sum(w * c))
        if denom <= 0.0:  # all confidences zero -> fall back to weight-only mean
            composite = float(np.sum(w * s) / np.sum(w))
        else:
            composite = float(np.sum(w * c * s) / denom)
        composite = max(-1.0, min(1.0, composite))
        score_0_100 = round((composite + 1.0) * 50.0, 2)

        considered = sum(1 for ds in scores if weights.get(ds.dimension.value, 0.0) > 0)
        data_suff = len(active) / max(1, considered)
        agreement = 1.0 - min(1.0, float(np.std(s))) if len(s) > 1 else 1.0
        avg_conf = float(np.mean(c))
        confidence = max(
            0.0, min(1.0, 0.4 * data_suff + 0.3 * agreement + 0.3 * avg_conf)
        )

        return FusionResult(
            as_of, composite, score_0_100, confidence, False,
            weights_version, contributions,
        )
