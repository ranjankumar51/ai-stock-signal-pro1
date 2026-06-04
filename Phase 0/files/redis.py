"""Redis integration.

Phase 0 provides only the connection lifecycle and a health check. The cache
and pub/sub responsibilities described in the architecture are layered on in
later phases. A single connection pool is shared process-wide.
"""
from __future__ import annotations

import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_client: redis.Redis | None = None


async def init_redis() -> redis.Redis:
    """Create the shared Redis client (called on app startup)."""
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
        log.info("redis.connected", url=_redacted_url())
    return _client


async def close_redis() -> None:
    """Dispose the client (called on app shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        log.info("redis.closed")


def get_client() -> redis.Redis:
    if _client is None:
        raise RuntimeError("Redis client not initialized; call init_redis() first.")
    return _client


async def ping() -> bool:
    """Liveness check used by the health endpoint."""
    try:
        return bool(await get_client().ping())
    except Exception as exc:  # noqa: BLE001 - report, don't crash health route
        log.warning("redis.ping_failed", error=str(exc))
        return False


def _redacted_url() -> str:
    return f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"


# FastAPI dependency
async def get_redis() -> redis.Redis:
    return get_client()
