"""Engine-level tests with an in-memory DataFeed and both clock types.

Proves the engine runs identically in live and backtest modes and that the
point-in-time feed prevents look-ahead (candles after as_of are invisible).
"""
from __future__ import annotations

import datetime as dt

from app.analysis.technical.engine import TechnicalAnalysisEngine
from app.ingestion.dto import Candle
from app.models.enums import Timeframe
from app.runtime.clock import LiveClock, SimulatedClock
from app.runtime.datafeed import DataFeed
from tests.factories import make_candles

UTC = dt.timezone.utc


class FakeFeed(DataFeed):
    """Serves pre-built candles, honoring the point-in-time `end` bound."""

    def __init__(self, candles: list[Candle]) -> None:
        self._candles = sorted(candles, key=lambda c: c.ts)

    async def get_candles(self, instrument_id, tf, *, end=None, limit=None):
        rows = [c for c in self._candles if end is None or c.ts <= end]
        if limit is not None:
            rows = rows[-limit:]
        return rows


def _uptrend(n=300):
    return make_candles([100.0 + i for i in range(n)])


def _downtrend(n=300):
    return make_candles([400.0 - i for i in range(n)])


async def test_engine_uptrend_bullish_live():
    candles = _uptrend()
    feed = FakeFeed(candles)
    clock = SimulatedClock(candles[-1].ts)  # as_of = last bar
    engine = TechnicalAnalysisEngine(feed, clock)
    res = await engine.analyze(instrument_id=1, tf=Timeframe.D1)
    assert not res.insufficient
    assert res.score_0_100 > 55
    assert res.confidence > 0
    assert "ema200" in res.indicators
    assert "atr" in res.indicators  # reported even though non-directional


async def test_engine_downtrend_bearish():
    candles = _downtrend()
    engine = TechnicalAnalysisEngine(FakeFeed(candles), SimulatedClock(candles[-1].ts))
    res = await engine.analyze(1, Timeframe.D1)
    assert res.score_0_100 < 45


async def test_point_in_time_no_lookahead():
    candles = _uptrend()
    feed = FakeFeed(candles)
    as_of = candles[100].ts  # only first 101 candles visible
    res = await TechnicalAnalysisEngine(feed, SimulatedClock(as_of)).analyze(1, Timeframe.D1)
    assert res.n_candles == 101


async def test_live_and_backtest_clock_same_result():
    candles = _uptrend()
    feed = FakeFeed(candles)
    sim = await TechnicalAnalysisEngine(feed, SimulatedClock(candles[-1].ts)).analyze(1, Timeframe.D1)
    # LiveClock.now() is "now" (>= last candle), so it also sees all candles
    live = await TechnicalAnalysisEngine(feed, LiveClock()).analyze(1, Timeframe.D1)
    assert sim.score_0_100 == live.score_0_100
