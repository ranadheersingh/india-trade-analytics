"""APScheduler setup. Registered pipelines run on their cron schedules."""
import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.ingestion import PIPELINES, get_pipeline

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler: AsyncIOScheduler | None = None


def _make_runner(name: str):
    async def _run():
        try:
            logger.info("[scheduler] running %s", name)
            pipe = get_pipeline(name)
            await pipe.run()
        except Exception as e:
            logger.exception("[scheduler] %s failed: %s", name, e)
    return _run


def start_scheduler() -> AsyncIOScheduler | None:
    global _scheduler
    if not settings.enable_scheduler:
        logger.info("[scheduler] disabled via ENABLE_SCHEDULER=false")
        return None
    if _scheduler is not None:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone="UTC")
    for name, cls in PIPELINES.items():
        if not cls.schedule_cron:
            continue
        try:
            trigger = CronTrigger.from_crontab(cls.schedule_cron, timezone="UTC")
            _scheduler.add_job(_make_runner(name), trigger=trigger, id=f"job_{name}", replace_existing=True)
            logger.info("[scheduler] registered %s with cron '%s'", name, cls.schedule_cron)
        except Exception as e:
            logger.error("[scheduler] failed to register %s: %s", name, e)

    _scheduler.start()
    logger.info("[scheduler] started")
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("[scheduler] stopped")
