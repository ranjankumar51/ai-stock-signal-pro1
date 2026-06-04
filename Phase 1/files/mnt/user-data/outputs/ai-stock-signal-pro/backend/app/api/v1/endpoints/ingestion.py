"""Ingestion control endpoints.

These only ENQUEUE work onto the Redis job queue and return 202 immediately.
The worker process performs the actual broker calls (sole rate-limited client).
"""
from fastapi import APIRouter, Depends, HTTPException, status

import redis.asyncio as redis

from app.core.redis import get_redis
from app.ingestion.intervals import parse_timeframe
from app.jobs.queue import Job, JobType, enqueue
from app.schemas.ingestion import (
    JobAccepted,
    SyncHistoricalRequest,
    SyncInstrumentsRequest,
)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post(
    "/instruments/sync",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sync_instruments(
    body: SyncInstrumentsRequest,
    client: redis.Redis = Depends(get_redis),
) -> JobAccepted:
    job = Job(
        type=JobType.SYNC_INSTRUMENTS,
        params={"also_constituents": body.also_constituents},
    )
    await enqueue(client, job)
    return JobAccepted(job_id=job.id, type=job.type.value)


@router.post(
    "/historical/sync",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sync_historical(
    body: SyncHistoricalRequest,
    client: redis.Redis = Depends(get_redis),
) -> JobAccepted:
    if not body.selector and not body.symbols:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either 'selector' or 'symbols'.",
        )
    # validate timeframes early so the caller gets a clear 422
    if body.timeframes:
        try:
            for tf in body.timeframes:
                parse_timeframe(tf)
        except (ValueError, KeyError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid timeframe in {body.timeframes}.",
            )

    job = Job(
        type=JobType.SYNC_HISTORICAL,
        params={
            "selector": body.selector,
            "symbols": body.symbols,
            "timeframes": body.timeframes,
            "lookback_days": body.lookback_days,
        },
    )
    await enqueue(client, job)
    return JobAccepted(job_id=job.id, type=job.type.value)
