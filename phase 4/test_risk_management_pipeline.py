"""Integration tests for the analysis-to-signal pipeline with risk management.

DB-free: driven with injected fakes (fake providers + fake repositories) so the
full fuse -> classify -> risk -> persist workflow runs without a database. A
final test wires the *real* Phase 2 technical engine to an in-memory FakeFeed to
prove end-to-end point-in-time correctness (the risk entry is taken from the
bounded last close) and LIVE/BACKTEST parity at the signal level.
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
from app.models.enums import ExecutionMode, SignalStatus, SignalType, TradeSide, Timeframe
from app.risk.engine import RiskParameters
from app.runtime.clock import LiveClock, SimulatedClock
from app.runtime.datafeed import DataFeed
from app.services.signal_generation import SignalGenerationService
from tests.factories import make_candles

UTC = dt.timezone.utc
WEIGHTS = {"technical": 0.4, "fundamental": 0.2, "news": 0.15, "social": 0.1, "volatility": 0.15}
RISK = RiskParameters(account_size=1_000_000.0, risk_per_trade_pct=0.01,
                      min_risk_reward=2.0, atr_stop_multiplier=1.5, target_rr=2.0)


class StubTechnical(ScoreProvider):
    dimension = Dimension.TECHNICAL

    def __init__(self, score, conf, *, close=100.0, atr=2.0,
                 resistance=200.0, support=80.0, available=True):
        self._s, self._c, self._a = score, conf, available
        self._close, self._atr = close, atr
        self._res, self._sup = resistance, support

    async def score(self, ctx):
        detail = {
            "score_norm": self._s,
            "score_0_100": (self._s + 1) * 50,
            "n_candles": 300,
            "close": self._close,
            "indicators": {
                "atr": {"values": {"atr": self._atr}},
                "support_resistance": {"values": {"resistance": self._res, "support": self._sup}},
            },
        }
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


def _service(tech, clock=None, snap=None, sig=None):
    return SignalGenerationService(
        session=None,
        clock=clock or LiveClock(),
        providers=[tech, *_placeholders()],
        weights=WEIGHTS,
        risk_params=RISK,
        snapshot_repo=snap,
        signal_repo=sig,
    )


async def test_strong_buy_with_valid_risk_is_active_with_plan():
    snap, sig = FakeSnapshotRepo(), FakeSignalRepo()
    gen = await _service(StubTechnical(0.9, 0.9), snap=snap, sig=sig).generate(
        1, Timeframe.D1, mode=ExecutionMode.LIVE
    )
    assert gen.classification.signal is SignalType.STRONG_BUY
    assert gen.status is SignalStatus.ACTIVE
    row = sig.rows[0]
    assert row["status"] is SignalStatus.ACTIVE
    assert float(row["entry"]) == 100.0
    assert float(row["stop_loss"]) == 97.0
    assert float(row["target"]) == 106.0
    assert float(row["risk_reward"]) == 2.0
    assert float(row["position_size"]) == 3333.0
    assert row["risk_confidence"] is not None
    assert gen.rationale["risk"]["accepted"] is True


async def test_risk_rejected_preserves_classification_and_nulls_plan():
    sig = FakeSnapshotRepo(), FakeSignalRepo()
    snap, sigr = sig
    # Resistance one rupee above entry -> achievable RR << 2 -> rejected.
    gen = await _service(StubTechnical(0.9, 0.9, resistance=101.0), snap=snap, sig=sigr).generate(
        1, Timeframe.D1
    )
    assert gen.classification.signal is SignalType.STRONG_BUY      # classification stands
    assert gen.status is SignalStatus.RISK_REJECTED
    row = sigr.rows[0]
    assert row["signal"] is SignalType.STRONG_BUY
    assert row["status"] is SignalStatus.RISK_REJECTED
    assert row["entry"] is None and row["stop_loss"] is None and row["target"] is None
    assert row["risk_reward"] is None and row["position_size"] is None
    assert row["risk_confidence"] is None
    assert gen.rationale["risk"]["reason"] == "risk_reward_below_minimum"


async def test_hold_has_no_risk_evaluation():
    sig = FakeSignalRepo()
    gen = await _service(StubTechnical(0.05, 0.9), snap=FakeSnapshotRepo(), sig=sig).generate(
        1, Timeframe.D1
    )
    assert gen.classification.signal is SignalType.HOLD
    assert gen.status is SignalStatus.ACTIVE
    assert gen.risk is None
    assert "risk" not in gen.rationale
    assert sig.rows[0]["entry"] is None


async def test_short_sell_with_valid_risk():
    sig = FakeSignalRepo()
    gen = await _service(StubTechnical(-0.8, 0.9), snap=FakeSnapshotRepo(), sig=sig).generate(
        1, Timeframe.D1
    )
    assert gen.classification.signal is SignalType.STRONG_SELL
    assert gen.classification.side is TradeSide.SHORT
    assert gen.status is SignalStatus.ACTIVE
    assert float(sig.rows[0]["stop_loss"]) == 103.0
    assert float(sig.rows[0]["target"]) == 94.0


async def test_live_backtest_parity():
    live = await _service(StubTechnical(0.9, 0.9), snap=FakeSnapshotRepo(), sig=FakeSignalRepo()).generate(
        1, Timeframe.D1, mode=ExecutionMode.LIVE
    )
    bt_sig = FakeSignalRepo()
    bt = await _service(
        StubTechnical(0.9, 0.9),
        clock=SimulatedClock(dt.datetime(2025, 1, 1, tzinfo=UTC)),
        snap=FakeSnapshotRepo(), sig=bt_sig,
    ).generate(1, Timeframe.D1, mode=ExecutionMode.BACKTEST, backtest_run_id=7)

    assert bt.classification.signal is live.classification.signal
    assert bt.status is live.status
    assert bt.entry == live.entry and bt.stop_loss == live.stop_loss
    assert bt.target == live.target and bt.risk_reward == live.risk_reward
    assert bt.position_size == live.position_size
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


async def test_real_engine_risk_entry_respects_no_lookahead():
    candles = make_candles([100.0 + i for i in range(300)])  # close[100] == 200.0
    feed = FakeFeed(candles)
    as_of = candles[100].ts                                   # only first 101 visible
    clock = SimulatedClock(as_of)
    engine = TechnicalAnalysisEngine(feed, clock)
    snap, sig = FakeSnapshotRepo(), FakeSignalRepo()
    svc = SignalGenerationService(
        session=None, clock=clock,
        providers=[TechnicalScoreProvider(engine), *_placeholders()],
        weights=WEIGHTS, risk_params=RISK, snapshot_repo=snap, signal_repo=sig,
    )
    gen = await svc.generate(1, Timeframe.D1, mode=ExecutionMode.BACKTEST, backtest_run_id=1)

    assert snap.rows[0]["details"]["n_candles"] == 101         # no future candles leaked
    assert "risk" in gen.rationale
    # entry is the bounded last close, never a future price
    assert gen.rationale["risk"]["entry"] == 200.0
