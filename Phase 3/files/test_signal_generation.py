"""Integration tests for the analysis-to-signal pipeline.

DB-free: the pipeline is driven with injected fakes (fake providers + fake
repositories) so the full fuse -> classify -> persist workflow is exercised
without a database. A second test wires the *real* Phase 2 technical engine to
an in-memory FakeFeed to prove end-to-end point-in-time correctness and
live/backtest parity at the signal level.
"""
from __future__ import annotations

import datetime as dt

from app.analysis.technical.engine import TechnicalAnalysisEngine
from app.fusion.dimensions import Dimension, DimensionScore, ScoreProvider
from app.fusion.providers.fundamental import FundamentalScoreProvider
from app.fusion.providers.news import NewsScoreProvider
from app.fusion.providers.social import SocialScoreProvider
from app.fusion.providers.technical import TechnicalScoreProvider
from app.fusion.providers.volatility import VolatilityScoreProvider
from app.ingestion.dto import Candle
from app.models.enums import ExecutionMode, SignalType, TradeSide, Timeframe
from app.runtime.clock import LiveClock, SimulatedClock
from app.runtime.datafeed import DataFeed
from app.services.signal_generation import SignalGenerationService
from tests.factories import make_candles

UTC = dt.timezone.utc
WEIGHTS = {"technical": 0.4, "fundamental": 0.2, "news": 0.15, "social": 0.1, "volatility": 0.15}


# --- fakes -----------------------------------------------------------------
class StubTechnical(ScoreProvider):
    dimension = Dimension.TECHNICAL

    def __init__(self, score: float, conf: float, available: bool = True) -> None:
        self._s, self._c, self._a = score, conf, available

    async def score(self, ctx):
        detail = {"score_norm": self._s, "score_0_100": (self._s + 1) * 50, "n_candles": 300}
        return DimensionScore(self.dimension, self._s, self._c, available=self._a, detail=detail)


class FakeSnapshotRepo:
    def __init__(self):
        self.rows = []

    async def upsert(self, **kw):
        kw["id"] = len(self.rows) + 1
        self.rows.append(kw)
        return kw["id"]


class FakeSignalRepo:
    def __init__(self):
        self.rows = []

    async def upsert(self, **kw):
        kw["id"] = len(self.rows) + 1
        self.rows.append(kw)
        return kw["id"]


def _placeholders():
    return [FundamentalScoreProvider(), NewsScoreProvider(), SocialScoreProvider(), VolatilityScoreProvider()]


def _service(tech, mode_clock=None, snap=None, sig=None):
    return SignalGenerationService(
        session=None,
        clock=mode_clock or LiveClock(),
        providers=[tech, *_placeholders()],
        weights=WEIGHTS,
        snapshot_repo=snap,
        signal_repo=sig,
    )


async def test_strong_bull_live_produces_strong_buy():
    snap, sig = FakeSnapshotRepo(), FakeSignalRepo()
    svc = _service(StubTechnical(0.9, 0.9), snap=snap, sig=sig)
    gen = await svc.generate(1, Timeframe.D1, mode=ExecutionMode.LIVE)

    assert gen.classification.signal is SignalType.STRONG_BUY
    assert gen.classification.side is TradeSide.LONG
    assert abs(gen.fusion.composite - 0.9) < 1e-9          # technical-only passthrough
    assert len(sig.rows) == 1 and len(snap.rows) == 1
    assert sig.rows[0]["mode"] is ExecutionMode.LIVE
    assert sig.rows[0]["backtest_run_id"] is None
    assert sig.rows[0]["snapshot_id"] == 1                  # signal linked to snapshot


async def test_strong_bear_produces_strong_sell():
    sig = FakeSignalRepo()
    svc = _service(StubTechnical(-0.8, 0.9), snap=FakeSnapshotRepo(), sig=sig)
    gen = await svc.generate(1, Timeframe.D1)
    assert gen.classification.signal is SignalType.STRONG_SELL
    assert gen.classification.side is TradeSide.SHORT


async def test_unavailable_technical_holds():
    sig = FakeSignalRepo()
    svc = _service(StubTechnical(0.9, 0.9, available=False), snap=FakeSnapshotRepo(), sig=sig)
    gen = await svc.generate(1, Timeframe.D1)
    assert gen.fusion.insufficient
    assert gen.classification.signal is SignalType.HOLD
    # snapshot still written, but tech_score is NULL when insufficient
    assert sig.rows[0]["signal"] is SignalType.HOLD


async def test_backtest_mode_tags_run_and_matches_live():
    live = await _service(StubTechnical(0.7, 0.9), snap=FakeSnapshotRepo(), sig=FakeSignalRepo()).generate(
        1, Timeframe.D1, mode=ExecutionMode.LIVE
    )
    bt_sig = FakeSignalRepo()
    bt = await _service(
        StubTechnical(0.7, 0.9), mode_clock=SimulatedClock(dt.datetime(2025, 1, 1, tzinfo=UTC)),
        snap=FakeSnapshotRepo(), sig=bt_sig,
    ).generate(1, Timeframe.D1, mode=ExecutionMode.BACKTEST, backtest_run_id=7)

    assert bt.classification.signal is live.classification.signal     # parity
    assert bt_sig.rows[0]["mode"] is ExecutionMode.BACKTEST
    assert bt_sig.rows[0]["backtest_run_id"] == 7


# --- real engine end-to-end (point-in-time / no-look-ahead) ----------------
class FakeFeed(DataFeed):
    def __init__(self, candles: list[Candle]):
        self._candles = sorted(candles, key=lambda c: c.ts)

    async def get_candles(self, instrument_id, tf, *, end=None, limit=None):
        rows = [c for c in self._candles if end is None or c.ts <= end]
        if limit is not None:
            rows = rows[-limit:]
        return rows


async def test_real_engine_no_lookahead_end_to_end():
    candles = make_candles([100.0 + i for i in range(300)])
    feed = FakeFeed(candles)
    as_of = candles[100].ts  # only first 101 candles visible
    clock = SimulatedClock(as_of)
    engine = TechnicalAnalysisEngine(feed, clock)
    snap, sig = FakeSnapshotRepo(), FakeSignalRepo()
    svc = SignalGenerationService(
        session=None, clock=clock,
        providers=[TechnicalScoreProvider(engine), *_placeholders()],
        weights=WEIGHTS, snapshot_repo=snap, signal_repo=sig,
    )
    gen = await svc.generate(1, Timeframe.D1, mode=ExecutionMode.BACKTEST, backtest_run_id=1)
    assert snap.rows[0]["details"]["n_candles"] == 101      # no future candles leaked
    assert gen.classification.signal in (SignalType.BUY, SignalType.STRONG_BUY)
