"""
Scheduler — runs default agent tasks automatically.
Schedule is driven by agent.config.yaml (schedule.prospect_time, schedule.inbox_interval_hours).
"""
from __future__ import annotations

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from core.agent import run_agent
from core.config_loader import get_config
from core.prompts import build_default_prospect_task, build_default_inbox_task
from core.logging import get_logger
from tools.telegram import telegram_notify

logger = get_logger("scheduler")


async def run_scheduled_task(task: str, mode: str, label: str) -> None:
    logger.info("scheduler.task_start", label=label)
    await telegram_notify(f"Scheduled task starting — {label}")

    try:
        async for event in run_agent(task=task, mode=mode):
            if event["type"] == "done":
                logger.info("scheduler.task_done", label=label, iterations=event.get("iterations"))
            elif event["type"] == "error":
                logger.error("scheduler.task_error", label=label, message=event.get("message"))
                await telegram_notify(f"Task error — {label}: {event.get('message')}")
    except Exception as e:
        logger.error("scheduler.exception", label=label, error=str(e))
        await telegram_notify(f"Task crashed — {label}: {e}")


def build_scheduler() -> AsyncIOScheduler:
    config = get_config()
    schedule = config.schedule

    # Parse prospect time
    hour, minute = map(int, schedule.prospect_time.split(":"))

    prospect_task = build_default_prospect_task(config)
    inbox_task = build_default_inbox_task(config)

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        run_scheduled_task,
        trigger=CronTrigger(hour=hour, minute=minute),
        args=[prospect_task, "prospect", "daily prospecting"],
        id="daily_prospect",
        replace_existing=True,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        run_scheduled_task,
        trigger=IntervalTrigger(hours=schedule.inbox_interval_hours),
        args=[inbox_task, "inbox", "inbox check"],
        id="inbox_check",
        replace_existing=True,
        misfire_grace_time=120,
    )

    return scheduler
