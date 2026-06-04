"""Timeframe mapping and Kite historical-API range limits.

Per-request day caps are imposed by Kite; the adapter chunks any longer range.
Source: Kite Connect historical-data limits (minute=60d, 5m/10m=100d,
15m/30m=200d, 60m=400d, day=2000d).
"""
from app.models.enums import Timeframe

KITE_INTERVAL: dict[Timeframe, str] = {
    Timeframe.M1: "minute",
    Timeframe.M5: "5minute",
    Timeframe.M15: "15minute",
    Timeframe.H1: "60minute",
    Timeframe.D1: "day",
}

# Maximum number of days fetchable in a single Kite historical request.
MAX_DAYS_PER_REQUEST: dict[Timeframe, int] = {
    Timeframe.M1: 60,
    Timeframe.M5: 100,
    Timeframe.M15: 200,
    Timeframe.H1: 400,
    Timeframe.D1: 2000,
}

# Timeframes supported in Phase 1 (per requirements: 1m, 5m, 15m, 1h, 1d).
PHASE1_TIMEFRAMES: list[Timeframe] = [
    Timeframe.M1,
    Timeframe.M5,
    Timeframe.M15,
    Timeframe.H1,
    Timeframe.D1,
]


def parse_timeframe(value: str) -> Timeframe:
    """Accept either the enum value ('1m') or the name ('M1')."""
    try:
        return Timeframe(value)
    except ValueError:
        return Timeframe[value]
