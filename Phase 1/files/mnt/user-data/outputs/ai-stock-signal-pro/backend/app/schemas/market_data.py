"""Schemas for market-data read endpoints."""
from pydantic import BaseModel


class LatestCandleResponse(BaseModel):
    symbol: str
    tf: str
    ts: str
    open: str
    high: str
    low: str
    close: str
    volume: int
    source: str  # "cache" | "db"


class LatestQuoteResponse(BaseModel):
    symbol: str
    last_price: str
    ts: str
