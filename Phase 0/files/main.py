"""FastAPI application entrypoint.

The app factory wires logging, the v1 router, and a lifespan context that
initializes Redis on startup and disposes the DB engine + Redis on shutdown.
No domain endpoints exist yet — Phase 0 stands up infrastructure only.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.redis import close_redis, init_redis
from app.db.session import dispose_engine

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log.info("app.startup", environment=settings.environment)
    await init_redis()
    yield
    await close_redis()
    await dispose_engine()
    log.info("app.shutdown")


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
