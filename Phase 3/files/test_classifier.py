"""Signal classifier — pure unit tests."""
from __future__ import annotations

from app.fusion.classifier import SignalClassifier
from app.models.enums import SignalType, TradeSide

C = SignalClassifier()


def test_strong_buy():
    r = C.classify(0.7, 0.9)
    assert r.signal is SignalType.STRONG_BUY
    assert r.side is TradeSide.LONG


def test_buy():
    r = C.classify(0.3, 0.9)
    assert r.signal is SignalType.BUY
    assert r.side is TradeSide.LONG


def test_hold_band():
    r = C.classify(0.05, 0.9)
    assert r.signal is SignalType.HOLD
    assert r.side is None


def test_sell():
    r = C.classify(-0.3, 0.9)
    assert r.signal is SignalType.SELL
    assert r.side is TradeSide.SHORT


def test_strong_sell():
    r = C.classify(-0.7, 0.9)
    assert r.signal is SignalType.STRONG_SELL
    assert r.side is TradeSide.SHORT


def test_low_confidence_forces_hold():
    # Strongly bullish composite but confidence below the gate -> HOLD.
    r = C.classify(0.9, 0.1)
    assert r.signal is SignalType.HOLD
    assert r.side is None


def test_threshold_boundaries():
    assert C.classify(0.5, 1.0).signal is SignalType.STRONG_BUY
    assert C.classify(0.15, 1.0).signal is SignalType.BUY
    assert C.classify(0.1499, 1.0).signal is SignalType.HOLD
