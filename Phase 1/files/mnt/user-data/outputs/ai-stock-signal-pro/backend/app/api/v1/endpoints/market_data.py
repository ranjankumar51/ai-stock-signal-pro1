"""Market-data read endpoints (served from Redis cache with DB fallback)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.db.session import get_db
from app.ingestion.intervals import parse_timeframe
from app.schemas.market_data import LatestCandleResponse, LatestQuoteResponse
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/{symbol}/latest", response_model=LatestCandleResponse)
async def latest_candle(
    symbol: str,
    tf: str = Query(default="1d", examples=["1m", "5m", "15m", "1h", "1d"]),
    db: AsyncSession = Depends(get_db),
    client: redis.Redis = Depends(get_redis),
) -> LatestCandleResponse:
    try:
        timeframe = parse_timeframe(tf)
    except (ValueError, KeyError):
        raise HTTPException(status_code=422, detail=f"Invalid timeframe: {tf}")

    data = await MarketDataService(client, db).get_latest_candle(symbol, timeframe)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data for {symbol} @ {tf}",
        )
    return LatestCandleResponse(**data)


@router.get("/{symbol}/quote", response_model=LatestQuoteResponse)
async def latest_quote(
    symbol: str,
    client: redis.Redis = Depends(get_redis),
) -> LatestQuoteResponse:
    data = await MarketDataService(client).get_latest_quote(symbol)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No cached quote for {symbol} (only available during market hours)",
        )
    return LatestQuoteResponse(**data)
