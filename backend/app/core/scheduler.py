"""
The timer that drives the agent.

One job, one instance at a time. If a cycle overruns the interval the next
firing is skipped rather than queued, so two cycles can never race for the
same position.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.core.agent import get_agent

logger = logging.getLogger(__name__)

JOB_ID = "gold_agent_cycle"

_scheduler: AsyncIOScheduler | None = None


async def _tick() -> None:
    await get_agent().cycle()


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _tick,
        trigger="interval",
        seconds=settings.SCAN_INTERVAL_SECONDS,
        id=JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30,
    )
    _scheduler.start()
    logger.info("Scheduler started — agent cycles every %ss", settings.SCAN_INTERVAL_SECONDS)
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    _scheduler = None


def scheduler_running() -> bool:
    return bool(_scheduler and _scheduler.running)
