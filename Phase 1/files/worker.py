"""Background worker.

Runs the recurring scheduler and the job-queue consumer in a single asyncio
process. This is the ONLY process that talks to the broker API, so its
in-process rate limiters are authoritative.

Scale path: replace the in-process queue/scheduler with Celery or RQ workers
behind a Redis broker; the service layer stays unchanged.
"""
from __future__ import annotations

import asyncio
import signal

from app.core.logging import configure_logging, get_logger
from app.core.redis import close_redis, get_client, init_redis
from app.db.session import dispose_engine
from app.jobs.queue import dequeue, dispatch
from app.jobs.scheduler import build_scheduler
from app.services.ingestion import IngestionService

log = get_logger(__name__)


async def _consume(svc: IngestionService, stop: asyncio.Event) -> None:
    client = get_client()
    while not stop.is_set():
        try:
            job = await dequeue(client, timeout=5)
            if job is not None:
                await dispatch(svc, job)
        except asyncio.CancelledError:  # pragma: no cover
            break
        except Exception as exc:  # noqa: BLE001 - keep the consumer alive
            log.error("worker.job_error", error=str(exc))
            await asyncio.sleep(1)


async def main() -> None:
    configure_logging()
    await init_redis()
    svc = IngestionService()
    log.info("worker.starting", provider=svc.provider.name, configured=svc.provider.is_configured())

    scheduler = build_scheduler(svc)
    scheduler.start()

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # pragma: no cover - non-unix
            pass

    try:
        await _consume(svc, stop)
    finally:
        scheduler.shutdown(wait=False)
        await close_redis()
        await dispose_engine()
        log.info("worker.stopped")


if __name__ == "__main__":
    asyncio.run(main())
