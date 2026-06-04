"""Schemas for ingestion endpoints."""
from pydantic import BaseModel, Field


class SyncInstrumentsRequest(BaseModel):
    also_constituents: bool = True


class SyncHistoricalRequest(BaseModel):
    # Either a selector (NIFTY50 | BANKNIFTY | ALL) or an explicit symbol list.
    selector: str | None = Field(default=None, examples=["NIFTY50", "BANKNIFTY", "ALL"])
    symbols: list[str] | None = Field(default=None, examples=[["RELIANCE", "INFY"]])
    timeframes: list[str] | None = Field(default=None, examples=[["1m", "5m", "15m", "1h", "1d"]])
    lookback_days: int | None = Field(default=None, ge=1, le=2000)


class JobAccepted(BaseModel):
    job_id: str
    type: str
    status: str = "accepted"
