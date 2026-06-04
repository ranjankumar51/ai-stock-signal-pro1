"""Recurring ingestion schedule (APScheduler, IST).

Jobs are market-hours aware where relevant; off-hours runs are cheap no-ops
(they fetch nothing new). All times are IST.

  * 08:30  daily   — refresh instrument master + constituents
  * every N min     — intraday OHLCV (1m/5m/15m) during market hours
  * hourly :01      — 60-minute candles during market hours
  * every K sec     — quote hot-cache refresh during market hours
  * 16:00  weekdays — end-of-day daily candle sync
"""
from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.logging import get_logger
from app.ingestion.constituents import SELECTOR_ALL
from app.jobs.market_hours import IST, is_market_open
from app.models.enums import Timeframe
from app.services.ingestion import IngestionService

log = get_logger(__name__)


def build_scheduler(svc: IngestionService) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=IST)

    async def instruments_job() -> None:
        await svc.run_sync_instruments(also_constituents=True)

    async def intraday_job() -> None:
        if not is_market_open():
            return
        await svc.run_sync_historical(
            {
                "selector": SELECTOR_ALL,
                "timeframes": [Timeframe.M1.value, Timeframe.M5.value, Timeframe.M15.value],
                "lookback_days": 1,
            }
        )

    async def hourly_job() -> None:
        if not is_market_open():
            return
        await svc.run_sync_historical(
            {"selector": SELECTOR_ALL, "timeframes": [Timeframe.H1.value], "lookback_days": 5}
        )

    async def eod_job() -> None:
        await svc.run_sync_historical(
            {"selector": SELECTOR_ALL, "timeframes": [Timeframe.D1.value], "lookback_days": 7}
        )

    async def quotes_job() -> None:
        if not is_market_open():
            return
        await svc.run_refresh_quotes()

    scheduler.add_job(instruments_job, CronTrigger(hour=8, minute=30), id="instruments", max_instances=1)
    scheduler.add_job(
        intraday_job,
        IntervalTrigger(minutes=settings.intraday_sync_interval_min),
        id="intraday_ohlcv",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(hourly_job, CronTrigger(minute=1), id="hourly_ohlcv", max_instances=1)
    scheduler.add_job(eod_job, CronTrigger(day_of_week="mon-fri", hour=16, minute=0), id="eod_daily", max_instances=1)
    scheduler.add_job(
        quotes_job,
        IntervalTrigger(seconds=settings.quote_refresh_sec),
        id="quotes_refresh",
        max_instances=1,
        coalesce=True,
    )
    log.info("scheduler.jobs_registered", jobs=[j.id for j in scheduler.get_jobs()])
    return scheduler
