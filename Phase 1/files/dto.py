"""Broker-agnostic DTOs.

Adapters translate vendor payloads into these so the rest of the system never
depends on a specific broker's field names or types.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import InstrumentType


@dataclass(slots=True)
class ProviderInstrument:
    symbol: str
    name: str
    instrument_type: InstrumentType
    exchange: str
    broker_token: str
    segment: str | None = None
    isin: str | None = None


@dataclass(slots=True)
class Candle:
    ts: dt.datetime  # timezone-aware, UTC
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(slots=True)
class QuoteTick:
    broker_token: str
    last_price: Decimal
    ts: dt.datetime  # UTC
