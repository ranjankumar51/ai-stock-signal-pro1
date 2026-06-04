"""Helpers to synthesize candles/series for indicator tests."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from app.analysis.technical.series import OHLCVSeries
from app.ingestion.dto import Candle

UTC = dt.timezone.utc


def make_candles(
    closes: list[float],
    start: dt.datetime | None = None,
    step: dt.timedelta = dt.timedelta(days=1),
    spread: float = 1.0,
    volume: float = 1000.0,
    volumes: list[float] | None = None,
) -> list[Candle]:
    start = start or dt.datetime(2025, 1, 1, tzinfo=UTC)
    candles: list[Candle] = []
    prev = closes[0]
    for i, c in enumerate(closes):
        vol = volumes[i] if volumes is not None else volume
        candles.append(
            Candle(
                ts=start + i * step,
                open=Decimal(str(prev)),
                high=Decimal(str(max(prev, c) + spread)),
                low=Decimal(str(min(prev, c) - spread)),
                close=Decimal(str(c)),
                volume=int(vol),
            )
        )
        prev = c
    return candles


def series(closes: list[float], **kw) -> OHLCVSeries:
    return OHLCVSeries.from_candles(make_candles(closes, **kw))
