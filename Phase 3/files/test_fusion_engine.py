"""Fusion scoring engine — pure unit tests (no DB)."""
from __future__ import annotations

import datetime as dt

from app.fusion.dimensions import Dimension, DimensionScore
from app.fusion.fusion_engine import FusionScoringEngine

AS_OF = dt.datetime(2025, 6, 1, tzinfo=dt.timezone.utc)
WEIGHTS = {"technical": 0.4, "fundamental": 0.2, "news": 0.15, "social": 0.1, "volatility": 0.15}


def _ds(dim, score, conf, available=True):
    return DimensionScore(dim, score, conf, available=available)


def test_single_available_dimension_passes_through():
    # Only technical available -> composite equals the technical score.
    scores = [
        _ds(Dimension.TECHNICAL, 0.8, 0.9),
        _ds(Dimension.FUNDAMENTAL, 0.0, 0.0, available=False),
        _ds(Dimension.NEWS, 0.0, 0.0, available=False),
        _ds(Dimension.SOCIAL, 0.0, 0.0, available=False),
        _ds(Dimension.VOLATILITY, 0.0, 0.0, available=False),
    ]
    res = FusionScoringEngine().aggregate(scores, WEIGHTS, AS_OF, weights_version=1)
    assert not res.insufficient
    assert abs(res.composite - 0.8) < 1e-9
    assert res.score_0_100 == 90.0
    assert res.weights_version == 1


def test_unavailable_dimensions_excluded():
    scores = [
        _ds(Dimension.TECHNICAL, 0.6, 1.0),
        _ds(Dimension.NEWS, -1.0, 1.0, available=False),  # would drag negative if counted
    ]
    res = FusionScoringEngine().aggregate(scores, WEIGHTS, AS_OF)
    assert abs(res.composite - 0.6) < 1e-9


def test_confidence_weighting_downweights_low_confidence():
    # Two available dims, equal weight; high-confidence bullish should dominate.
    w = {"technical": 1.0, "news": 1.0}
    scores = [_ds(Dimension.TECHNICAL, 1.0, 0.9), _ds(Dimension.NEWS, -1.0, 0.1)]
    res = FusionScoringEngine().aggregate(scores, w, AS_OF)
    # (1*0.9*1 + 1*0.1*-1) / (0.9+0.1) = 0.8
    assert abs(res.composite - 0.8) < 1e-9


def test_all_unavailable_is_insufficient_neutral():
    scores = [_ds(Dimension.TECHNICAL, 0.5, 0.5, available=False)]
    res = FusionScoringEngine().aggregate(scores, WEIGHTS, AS_OF)
    assert res.insufficient
    assert res.composite == 0.0
    assert res.score_0_100 == 50.0
    assert res.confidence == 0.0


def test_zero_weight_dimension_excluded():
    w = {"technical": 0.0}  # technical present but zero-weighted
    res = FusionScoringEngine().aggregate([_ds(Dimension.TECHNICAL, 0.9, 0.9)], w, AS_OF)
    assert res.insufficient


def test_disagreement_lowers_confidence():
    w = {"technical": 1.0, "fundamental": 1.0}
    agree = FusionScoringEngine().aggregate(
        [_ds(Dimension.TECHNICAL, 0.8, 0.9), _ds(Dimension.FUNDAMENTAL, 0.8, 0.9)], w, AS_OF
    )
    disagree = FusionScoringEngine().aggregate(
        [_ds(Dimension.TECHNICAL, 0.8, 0.9), _ds(Dimension.FUNDAMENTAL, -0.8, 0.9)], w, AS_OF
    )
    assert disagree.confidence < agree.confidence


def test_rationale_carries_all_dimensions():
    scores = [_ds(Dimension.TECHNICAL, 0.5, 0.8), _ds(Dimension.NEWS, 0.0, 0.0, available=False)]
    res = FusionScoringEngine().aggregate(scores, WEIGHTS, AS_OF)
    r = res.to_rationale("1d")
    assert set(["technical", "news"]).issubset(r["dimensions"].keys())
    assert r["dimensions"]["news"]["available"] is False
