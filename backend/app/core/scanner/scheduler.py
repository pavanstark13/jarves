"""
APScheduler setup for the 5-minute strategy scanner.
Integrated into FastAPI lifespan in main.py.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.scanner.scanner_engine import scanner

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        scanner.run_scan,
        trigger="interval",
        minutes=5,
        id="main_scanner",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — scanner fires every 5 minutes")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
