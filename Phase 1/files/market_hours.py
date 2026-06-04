"""NSE market-hours helpers (IST).

Phase 1 handles weekday session hours only (09:15–15:30 IST). A trading-holiday
calendar is a later refinement; until then, scheduled jobs may run on holidays
and simply fetch no new data.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = dt.time(9, 15)
MARKET_CLOSE = dt.time(15, 30)


def now_ist() -> dt.datetime:
    return dt.datetime.now(tz=IST)


def is_market_open(at: dt.datetime | None = None) -> bool:
    at = at or now_ist()
    if at.tzinfo is None:
        at = at.replace(tzinfo=IST)
    at = at.astimezone(IST)
    if at.weekday() >= 5:  # Sat/Sun
        return False
    return MARKET_OPEN <= at.time() <= MARKET_CLOSE
