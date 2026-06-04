"""Schemas for signal endpoints."""
from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateSignalRequest(BaseModel):
    symbol: str = Field(examples=["RELIANCE", "NIFTY 50"])
    tf: str = Field(default="1d", examples=["1m", "5m", "15m", "1h", "1d"])


class SignalResponse(BaseModel):
    instrument_id: int
    symbol: str
    tf: str
    ts: str
    signal: str
    composite_score: float
    score_0_100: float
    confidence: float
    side: str | None
    status: str
    weights_version: int | None
    snapshot_id: int | None
    rationale: dict
    mode: str
