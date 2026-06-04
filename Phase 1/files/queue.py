"""Lightweight Redis-list job queue.

The API enqueues jobs; the worker consumes them. This keeps all broker access
in the worker process (authoritative rate limiting) while letting the API
return immediately. For higher throughput / multi-node this can be swapped for
Celery or RQ without changing the service layer.
"""
from __future__ import annotations

import enum
import json
import uuid

import redis.asyncio as redis
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ingestion import IngestionService

log = get_logger(__name__)


class JobType(str, enum.Enum):
    SYNC_INSTRUMENTS = "SYNC_INSTRUMENTS"
    SYNC_CONSTITUENTS = "SYNC_CONSTITUENTS"
    SYNC_HISTORICAL = "SYNC_HISTORICAL"


class Job(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    type: JobType
    params: dict = Field(default_factory=dict)


async def enqueue(redis_client: redis.Redis, job: Job) -> str:
    await redis_client.lpush(settings.job_queue_key, job.model_dump_json())
    log.info("job.enqueued", id=job.id, type=job.type.value)
    return job.id


async def dequeue(redis_client: redis.Redis, timeout: int = 5) -> Job | None:
    res = await redis_client.brpop([settings.job_queue_key], timeout=timeout)
    if res is None:
        return None
    _, raw = res
    return Job.model_validate_json(raw)


async def dispatch(svc: IngestionService, job: Job) -> None:
    log.info("job.dispatch", id=job.id, type=job.type.value)
    if job.type is JobType.SYNC_INSTRUMENTS:
        await svc.run_sync_instruments(
            also_constituents=job.params.get("also_constituents", True)
        )
    elif job.type is JobType.SYNC_CONSTITUENTS:
        await svc.run_sync_constituents()
    elif job.type is JobType.SYNC_HISTORICAL:
        await svc.run_sync_historical(job.params)
    else:  # pragma: no cover
        log.warning("job.unknown_type", type=str(job.type))
