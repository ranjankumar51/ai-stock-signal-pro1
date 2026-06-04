"""Provider factory.

Returns the configured market-data adapter. Adding Upstox/Angel One later is a
new branch here plus a new adapter class — callers are unaffected.
"""
from app.core.config import settings
from app.ingestion.providers.base import MarketDataProvider
from app.ingestion.providers.zerodha import ZerodhaProvider


def get_market_data_provider() -> MarketDataProvider:
    provider = settings.broker_provider.lower()
    if provider == "zerodha":
        return ZerodhaProvider()
    raise ValueError(f"Unsupported broker_provider: {settings.broker_provider!r}")
