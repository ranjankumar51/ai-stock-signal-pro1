"""Risk management engine — pure unit tests (no DB, no clock)."""
from __future__ import annotations

from app.models.enums import TradeSide
from app.risk.engine import RiskManagementEngine, RiskParameters

P = RiskParameters(
    account_size=1_000_000.0,
    risk_per_trade_pct=0.01,   # -> 10,000 capital at risk
    min_risk_reward=2.0,
    atr_stop_multiplier=1.5,
    target_rr=2.0,
)
ENG = RiskManagementEngine(P)


def test_long_accept_full_rr():
    r = ENG.evaluate(side=TradeSide.LONG, entry=100.0, atr=2.0, signal_confidence=0.8,
                     resistance=200.0, support=80.0)
    assert r.accepted
    assert abs(r.stop_loss - 97.0) < 1e-9        # 100 - 2*1.5
    assert abs(r.target - 106.0) < 1e-9          # 100 + 2*(2*1.5)
    assert abs(r.risk_reward - 2.0) < 1e-9
    assert r.position_size == 3333               # floor(10000 / 3)
    assert abs(r.risk_confidence - 0.48) < 1e-9  # 0.6*0.8 + 0.4*0


def test_long_reject_when_resistance_caps_rr():
    r = ENG.evaluate(side=TradeSide.LONG, entry=100.0, atr=2.0, signal_confidence=0.9,
                     resistance=104.0, support=80.0)
    assert not r.accepted
    assert r.reason == "risk_reward_below_minimum"
    assert r.entry is None and r.stop_loss is None and r.target is None
    assert r.risk_reward is None and r.position_size is None and r.risk_confidence is None
    assert r.detail["entry"] == 100.0            # context retained for rationale


def test_long_resistance_above_ideal_is_not_a_cap():
    r = ENG.evaluate(side=TradeSide.LONG, entry=100.0, atr=2.0, signal_confidence=0.9,
                     resistance=110.0)
    assert r.accepted
    assert abs(r.target - 106.0) < 1e-9
    assert abs(r.risk_reward - 2.0) < 1e-9


def test_long_no_levels_accepts():
    r = ENG.evaluate(side=TradeSide.LONG, entry=100.0, atr=2.0, signal_confidence=0.5)
    assert r.accepted and abs(r.risk_reward - 2.0) < 1e-9


def test_short_accept():
    r = ENG.evaluate(side=TradeSide.SHORT, entry=100.0, atr=2.0, signal_confidence=0.7,
                     support=80.0, resistance=120.0)
    assert r.accepted
    assert abs(r.stop_loss - 103.0) < 1e-9
    assert abs(r.target - 94.0) < 1e-9
    assert abs(r.risk_reward - 2.0) < 1e-9


def test_short_reject_when_support_caps_rr():
    r = ENG.evaluate(side=TradeSide.SHORT, entry=100.0, atr=2.0, signal_confidence=0.7,
                     support=97.0)
    assert not r.accepted
    assert r.reason == "risk_reward_below_minimum"


def test_invalid_atr_rejects():
    r = ENG.evaluate(side=TradeSide.LONG, entry=100.0, atr=0.0, signal_confidence=0.9)
    assert not r.accepted and r.reason == "invalid_inputs"


def test_no_side_rejects():
    r = ENG.evaluate(side=None, entry=100.0, atr=2.0, signal_confidence=0.9)
    assert not r.accepted and r.reason == "no_side"


def test_position_size_below_one_rejects():
    tiny = RiskParameters(account_size=1.0, risk_per_trade_pct=0.01, min_risk_reward=2.0,
                          atr_stop_multiplier=1.5, target_rr=2.0)
    r = RiskManagementEngine(tiny).evaluate(
        side=TradeSide.LONG, entry=100.0, atr=2.0, signal_confidence=0.9, resistance=200.0
    )
    assert not r.accepted and r.reason == "position_size_below_one"


def test_partial_cap_accepts_with_lower_rr_and_headroom():
    params = RiskParameters(account_size=1_000_000.0, risk_per_trade_pct=0.01,
                            min_risk_reward=2.0, atr_stop_multiplier=1.5, target_rr=3.0)
    # risk/unit=3, ideal target=109, resistance 107.5 -> reward 7.5 -> rr 2.5 (>= min 2)
    r = RiskManagementEngine(params).evaluate(
        side=TradeSide.LONG, entry=100.0, atr=2.0, signal_confidence=0.8, resistance=107.5
    )
    assert r.accepted
    assert abs(r.risk_reward - 2.5) < 1e-9
    # headroom = (2.5-2)/2 = 0.25 -> conf = 0.6*0.8 + 0.4*0.25 = 0.58
    assert abs(r.risk_confidence - 0.58) < 1e-9
