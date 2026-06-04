"""Indicator registry (Strategy registry) and default composite weights.

Swap or reweight indicators here without touching the engine. Non-directional
indicators (ATR) carry no weight in the directional composite.
"""
from __future__ import annotations

from app.analysis.technical.base import Indicator
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

DEFAULT_WEIGHTS: dict[str, float] = {
    "ema20": 1.0,
    "ema50": 1.2,
    "ema200": 1.5,
    "macd": 1.3,
    "rsi": 1.0,
    "adx": 1.2,
    "supertrend": 1.3,
    "bollinger": 0.8,
    "vwap": 0.9,
    "volume": 0.6,
    "support_resistance": 0.7,
    # atr is non-directional -> no composite weight
}


def default_indicators() -> list[Indicator]:
    return [
        EMAIndicator(20),
        EMAIndicator(50),
        EMAIndicator(200),
        MACDIndicator(),
        RSIIndicator(),
        ADXIndicator(),
        SuperTrendIndicator(),
        BollingerIndicator(),
        VWAPIndicator(),
        VolumeIndicator(),
        SupportResistanceIndicator(),
        ATRIndicator(),
    ]
