"""
LinkedIn post scheduler.

Flow per scheduled run:
  1. Pick a topic from config (rotates through the list)
  2. Generate a post using Claude + user's voice/examples
  3. Send to Telegram for approval with [Post] / [Reject] / [Edit] buttons
  4. On approval - post_linkedin()
  5. On rejection - skip, log
  6. On edit - user sends the edited text back, then confirm again
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime

import anthropic
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core.config import settings
from core.config_loader import get_config, ContentConfig
from core.logging import get_logger
from tools.linkedin_post import post_linkedin
from tools.telegram import telegram_ask, telegram_notify

logger = get_logger("post_scheduler")

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

DAY_MAP = {
    "mon": "mon",
    "tue": "tue",
    "wed": "wed",
    "thu": "thu",
    "fri": "fri",
    "sat": "sat",
    "sun": "sun",
}

# Track topic rotation across runs
_last_topic_index: int = -1


def _pick_topic(content: ContentConfig) -> str:
    global _last_topic_index
    if not content.topics:
        return "something valuable from your work this week"
    _last_topic_index = (_last_topic_index + 1) % len(content.topics)
    return content.topics[_last_topic_index]


def _generate_post(content: ContentConfig, topic: str) -> str:
    """Call Claude to generate a LinkedIn post matching the user's voice."""
    examples_block = ""
    if content.examples:
        formatted = "\n\n---\n\n".join(content.examples[:2])
        examples_block = (
            f"\n\nHere are examples of posts in their voice:\n\n{formatted}"
        )

    system = (
        f"You write LinkedIn posts for a specific person. "
        f"Your job is to match their voice exactly.\n\n"
        f"Their voice: {content.voice}\n"
        f"Format: {content.format.style}\n"
        f"Length: {content.format.length}\n"
        f"CTA: {content.format.cta}\n"
        f"{examples_block}\n\n"
        f"Return ONLY the post text. No quotes, no preamble, no hashtags unless they naturally fit."
    )

    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": f"Write a LinkedIn post about: {topic}"}],
    )
    return response.content[0].text.strip()


async def _approval_flow(post_text: str) -> tuple[bool, str]:
    """
    Send post to Telegram for approval.
    Returns (approved: bool, final_text: str).

    Buttons: Post / Edit / Reject
    If Edit: user sends the edited version as a follow-up message,
             then we ask for final confirmation.
    """
    msg = (
        f"LinkedIn post ready for approval\n"
        f"───────────────────\n\n"
        f"{post_text}\n\n"
        f"───────────────────\n"
        f"Post this?"
    )

    result = await telegram_ask(
        message=msg,
        options=["Post", "Edit", "Reject"],
    )

    response = result.get("response", "Reject")

    if response == "Post":
        return True, post_text

    if response == "Reject":
        return False, post_text

    if response == "Edit":
        # Ask user to send the edited version
        await telegram_notify(
            "Send me the edited post text as a message and I will confirm before posting."
        )
        # Wait for the next plain text message via a short-lived future
        edited = await _wait_for_edit(timeout=600)
        if not edited:
            await telegram_notify("No edit received within 10 minutes — post skipped.")
            return False, post_text

        # Confirm the edited version
        confirm = await telegram_ask(
            message=f"Post this edited version?\n\n───────────────────\n\n{edited}\n\n───────────────────",
            options=["Post", "Reject"],
        )
        if confirm.get("response") == "Post":
            return True, edited
        return False, edited

    return False, post_text


# Simple future for waiting on an edit message from Telegram
_edit_future: asyncio.Future | None = None


async def _wait_for_edit(timeout: int = 600) -> str | None:
    global _edit_future
    loop = asyncio.get_event_loop()
    _edit_future = loop.create_future()
    try:
        return await asyncio.wait_for(_edit_future, timeout=timeout)
    except asyncio.TimeoutError:
        return None
    finally:
        _edit_future = None


def resolve_edit(text: str) -> bool:
    """Called by the Telegram receiver when a plain message arrives during an edit wait."""
    global _edit_future
    if _edit_future and not _edit_future.done():
        _edit_future.set_result(text)
        return True
    return False


async def run_post_job() -> None:
    """Main scheduled job — generate, approve, post."""
    config = get_config()
    content = config.content

    if not content.schedule.enabled:
        logger.info("post_scheduler.disabled")
        return

    topic = _pick_topic(content)
    logger.info("post_scheduler.generating", topic=topic)

    try:
        post_text = _generate_post(content, topic)
        logger.info("post_scheduler.generated", chars=len(post_text))
    except Exception as e:
        logger.error("post_scheduler.generation_error", error=str(e))
        await telegram_notify(f"Post generation failed: {e}")
        return

    approved, final_text = await _approval_flow(post_text)

    if not approved:
        logger.info("post_scheduler.rejected")
        await telegram_notify("Post rejected — skipped.")
        return

    result = await post_linkedin(final_text)

    if result.get("success"):
        method = result.get("method", "unknown")
        logger.info("post_scheduler.posted", method=method)
        await telegram_notify(f"Post published via {method}.")
    else:
        error = result.get("error", "unknown error")
        logger.error("post_scheduler.post_failed", error=error)
        await telegram_notify(f"Post failed: {error}")


def build_post_scheduler() -> AsyncIOScheduler:
    """Build scheduler jobs from content.schedule config."""
    config = get_config()
    content = config.content
    sched = content.schedule

    scheduler = AsyncIOScheduler()

    if not sched.enabled:
        logger.info("post_scheduler.schedule_disabled")
        return scheduler

    days_str = ",".join(DAY_MAP.get(d.lower(), d) for d in sched.days)

    for time_str in sched.times:
        hour, minute = map(int, time_str.split(":"))
        job_id = f"linkedin_post_{time_str.replace(':', '')}"

        scheduler.add_job(
            run_post_job,
            trigger=CronTrigger(day_of_week=days_str, hour=hour, minute=minute),
            id=job_id,
            replace_existing=True,
            misfire_grace_time=300,
        )
        logger.info(
            "post_scheduler.job_added",
            job_id=job_id,
            days=days_str,
            time=time_str,
        )

    return scheduler
