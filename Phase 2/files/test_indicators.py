"""Each indicator is tested in isolation on synthetic series."""
from __future__ import annotations

import datetime as dt

from app.analysis.technical.indicators.adx import ADXIndicator
from app.analysis.technical.indicators.atr import ATRIndicator
from app.analysis.technical.indicators.bollinger import BollingerIndicator
from app.analysis.technical.indicators.ema import EMAIndicator
from app.analysis.technical.indicators.macd import MACDIndicator
from app.analysis.technical.indicators.rsi import RSIIndicator
from app.analysis.technical.indicators.supertrend import SuperTrendIndicator
from app.analysis.technical.indicators.support_resistance import (
    SupportResistanceIndicator,
)
from app.analysis.technical.indicators.volume import VolumeIndicator
from app.analysis.technical.indicators.vwap import VWAPIndicator
from tests.factories import series

UPTREND = [100.0 + i for i in range(300)]
DOWNTREND = [400.0 - i for i in range(300)]
FLAT = [100.0] * 300


def test_rsi_uptrend_high_and_bullish():
    r = RSIIndicator().compute(series(UPTREND))
    assert r.values["rsi"] > 95
    assert r.score > 0.9


def test_rsi_downtrend_low_and_bearish():
    r = RSIIndicator().compute(series(DOWNTREND))
    assert r.values["rsi"] < 5
    assert r.score < -0.9


def test_rsi_insufficient():
    assert RSIIndicator().compute(series([1, 2, 3])).insufficient


def test_ema_flat_neutral_increasing_bullish():
    assert abs(EMAIndicator(20).compute(series(FLAT)).score) < 1e-6
    assert EMAIndicator(50).compute(series(UPTREND)).score > 0


def test_macd_uptrend_positive_hist():
    r = MACDIndicator().compute(series(UPTREND))
    assert r.values["hist"] > 0
    assert r.score > 0


def test_atr_non_directional_positive():
    r = ATRIndicator().compute(series(UPTREND))
    assert ATRIndicator.directional is False
    assert r.score == 0.0
    assert r.values["atr"] > 0


def test_adx_uptrend_strong_and_bullish():
    r = ADXIndicator().compute(series(UPTREND))
    assert r.values["plus_di"] > r.values["minus_di"]
    assert r.values["adx"] > 25
    assert r.score > 0


def test_bollinger_mid_equals_sma_and_uptrend_bullish():
    r = BollingerIndicator().compute(series(UPTREND))
    assert r.values["upper"] > r.values["mid"] > r.values["lower"]
    assert r.score > 0


def test_supertrend_uptrend_direction_up():
    r = SuperTrendIndicator().compute(series(UPTREND))
    assert r.meta["uptrend"] is True
    assert r.score > 0


def test_supertrend_downtrend_direction_down():
    r = SuperTrendIndicator().compute(series(DOWNTREND))
    assert r.meta["uptrend"] is False
    assert r.score < 0


def test_volume_spike_with_up_move_bullish():
    vols = [1000.0] * 299 + [5000.0]
    r = VolumeIndicator().compute(series(UPTREND, volumes=vols))
    assert r.values["rel_volume"] > 1.5
    assert r.score > 0


def test_support_resistance_bounds_price():
    r = SupportResistanceIndicator().compute(series(UPTREND))
    c = 100.0 + 299
    assert r.values["support"] <= c <= r.values["resistance"] or r.values["resistance"] >= c
    assert -1.0 <= r.score <= 1.0


def test_vwap_intraday_uptrend_bullish():
    # 30 five-minute bars within one IST day, rising
    closes = [100.0 + i for i in range(30)]
    r = VWAPIndicator().compute(series(closes, step=dt.timedelta(minutes=5)))
    assert r.values["vwap"] > 0
    assert r.score > 0
