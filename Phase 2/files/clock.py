"""Clock abstraction.

Engines must take their notion of "now" from an injected Clock instead of
calling ``datetime.now`` directly. Live mode uses the wall clock; backtest mode
uses a SimulatedClock the runner advances bar by bar. Same engine code, two
modes.
"""
from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod

UTC = dt.timezone.utc


class Clock(ABC):
    @abstractmethod
    def now(self) -> dt.datetime:
        """Current time as a timezone-aware UTC datetime."""


class LiveClock(Clock):
    def now(self) -> dt.datetime:
        return dt.datetime.now(tz=UTC)


class SimulatedClock(Clock):
    """Backtest clock. The runner sets/advances ``now`` as it replays bars.

    Because every read goes through ``now()``, a DataFeed bounded by ``now()``
    structurally prevents look-ahead.
    """

    def __init__(self, start: dt.datetime) -> None:
        self._now = _as_utc(start)

    def now(self) -> dt.datetime:
        return self._now

    def set(self, ts: dt.datetime) -> None:
        self._now = _as_utc(ts)

    def advance(self, delta: dt.timedelta) -> dt.datetime:
        self._now = self._now + delta
        return self._now


def _as_utc(ts: dt.datetime) -> dt.datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)
