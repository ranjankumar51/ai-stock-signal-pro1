"""Enum definitions shared by Python code and the PostgreSQL schema.

The PGEnum objects use ``create_type=False`` because the enum types are created
explicitly in the Alembic migration (single source of truth for DDL).
``values_callable`` ensures the stored DB labels match the enum *values*.
"""
import enum

from sqlalchemy.dialects.postgresql import ENUM as PGEnum


class InstrumentType(str, enum.Enum):
    STOCK = "STOCK"
    INDEX = "INDEX"


class Timeframe(str, enum.Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    D1 = "1d"
    W1 = "1w"


class SignalType(str, enum.Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class SignalStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    TRIGGERED = "TRIGGERED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"


class TradeSide(str, enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class TradeOutcome(str, enum.Enum):
    OPEN = "OPEN"
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"


class SentimentLabel(str, enum.Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


def _pg(py_enum: type[enum.Enum], name: str) -> PGEnum:
    return PGEnum(
        py_enum,
        name=name,
        create_type=False,
        values_callable=lambda e: [m.value for m in e],
    )


instrument_type_enum = _pg(InstrumentType, "instrument_type")
timeframe_enum = _pg(Timeframe, "timeframe")
signal_type_enum = _pg(SignalType, "signal_type")
signal_status_enum = _pg(SignalStatus, "signal_status")
trade_side_enum = _pg(TradeSide, "trade_side")
trade_outcome_enum = _pg(TradeOutcome, "trade_outcome")
sentiment_label_enum = _pg(SentimentLabel, "sentiment_label")
