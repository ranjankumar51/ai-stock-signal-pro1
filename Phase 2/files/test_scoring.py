import datetime as dt

from app.analysis.technical.scoring import (
    ScoredItem,
    TechnicalScoringEngine,
    TechnicalTrend,
)

AS_OF = dt.datetime(2025, 6, 1, tzinfo=dt.timezone.utc)


def _items(score: float, n: int = 5) -> list[ScoredItem]:
    return [
        ScoredItem(f"i{k}", score=score, confidence=0.8, directional=True, weight=1.0, insufficient=False)
        for k in range(n)
    ]


def test_all_bullish_maps_to_strong_bullish():
    res = TechnicalScoringEngine().aggregate(_items(0.8), AS_OF, 300)
    assert res.score_0_100 == 90.0
    assert res.trend == TechnicalTrend.STRONG_BULLISH.value
    assert res.confidence > 0.7


def test_all_bearish_maps_to_strong_bearish():
    res = TechnicalScoringEngine().aggregate(_items(-0.8), AS_OF, 300)
    assert res.score_0_100 == 10.0
    assert res.trend == TechnicalTrend.STRONG_BEARISH.value


def test_neutral_midpoint():
    res = TechnicalScoringEngine().aggregate(_items(0.0), AS_OF, 300)
    assert res.score_0_100 == 50.0
    assert res.trend == TechnicalTrend.NEUTRAL.value


def test_no_valid_indicators_is_insufficient():
    items = [
        ScoredItem("x", 0.0, 0.0, directional=True, weight=1.0, insufficient=True),
        ScoredItem("atr", 0.0, 1.0, directional=False, weight=0.0, insufficient=False),
    ]
    res = TechnicalScoringEngine().aggregate(items, AS_OF, 5)
    assert res.insufficient is True
    assert res.confidence == 0.0
    assert res.trend == TechnicalTrend.NEUTRAL.value


def test_disagreement_lowers_confidence():
    mixed = [
        ScoredItem("a", 0.9, 0.8, True, 1.0, False),
        ScoredItem("b", -0.9, 0.8, True, 1.0, False),
        ScoredItem("c", 0.9, 0.8, True, 1.0, False),
        ScoredItem("d", -0.9, 0.8, True, 1.0, False),
    ]
    agree = TechnicalScoringEngine().aggregate(_items(0.9, 4), AS_OF, 300)
    disagree = TechnicalScoringEngine().aggregate(mixed, AS_OF, 300)
    assert disagree.confidence < agree.confidence
