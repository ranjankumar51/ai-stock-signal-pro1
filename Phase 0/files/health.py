"""Health and readiness probes.

  * GET /health  -> liveness; always 200 if the process is up.
  * GET /ready   -> readiness; verifies DB and Redis, 503 if degraded.

No business logic here — Phase 0 only proves the infrastructure is wired.
"""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import redis as redis_mod
from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import ComponentHealth, HealthResponse

router = APIRouter(tags=["health"])

VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness: the process is running."""
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        version=VERSION,
        components=ComponentHealth(database=True, redis=True),
    )


@router.get("/ready", response_model=HealthResponse)
async def ready(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    """Readiness: dependencies reachable."""
    db_ok = await _check_db(db)
    redis_ok = await redis_mod.ping()
    healthy = db_ok and redis_ok

    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ok" if healthy else "degraded",
        environment=settings.environment,
        version=VERSION,
        components=ComponentHealth(database=db_ok, redis=redis_ok),
    )


async def _check_db(db: AsyncSession) -> bool:
    try:
        await db.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False
