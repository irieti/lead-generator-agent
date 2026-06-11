"""
Telegram task receiver.

You send any message to the bot — it runs it as an agent task.
The same approval gates apply as with scheduled tasks.

Commands:
  /status   — show scheduled jobs and agent status
  /stop     — cancel the currently running task
  /prospect — run prospect mode immediately
  /inbox    — run inbox check immediately
  Any other text — treated as a custom task
"""
from __future__ import annotations

import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from core.agent import run_agent
from core.post_scheduler import resolve_edit
from core.logging import get_logger

logger = get_logger("telegram.receiver")

# Currently running task (only one at a time)
_current_task: asyncio.Task | None = None


async def _run_and_stream(task: str, mode: str, update: Update) -> None:
    """Run the agent and send status updates back to Telegram."""
    global _current_task

    await update.message.reply_text(f"Starting — {mode.upper()} mode\nTask: {task[:120]}...")

    try:
        async for event in run_agent(task=task, mode=mode):
            if event["type"] == "tool_call":
                tool = event["tool"]
                inputs = event.get("inputs", {})
                # Send a brief update for each tool call
                preview = str(inputs)[:80]
                await update.message.reply_text(f"[ {tool} ] {preview}")

            elif event["type"] == "thinking" and len(event.get("content", "")) > 20:
                await update.message.reply_text(f"Thinking: {event['content'][:200]}")

            elif event["type"] == "done":
                output = event.get("output", "")
                await update.message.reply_text(
                    f"Done — {event.get('iterations', 0)} steps\n\n{output[:800]}"
                    if output else f"Done — {event.get('iterations', 0)} steps"
                )

            elif event["type"] == "error":
                await update.message.reply_text(f"Error: {event.get('message')}")

    except asyncio.CancelledError:
        await update.message.reply_text("Task cancelled.")
    except Exception as e:
        logger.error("telegram.receiver.error", error=str(e))
        await update.message.reply_text(f"Crashed: {e}")
    finally:
        _current_task = None


async def _start_task(task: str, mode: str, update: Update) -> None:
    """Cancel any running task and start a new one."""
    global _current_task

    if _current_task and not _current_task.done():
        _current_task.cancel()
        await update.message.reply_text("Previous task cancelled. Starting new one...")

    _current_task = asyncio.create_task(
        _run_and_stream(task, mode, update)
    )


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Agent online.\n\n"
        "Send any task in plain text and I will execute it.\n\n"
        "Commands:\n"
        "/prospect — run daily prospecting now\n"
        "/inbox    — check inbox now\n"
        "/status   — show current state\n"
        "/stop     — cancel running task"
    )


async def cmd_prospect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    task = (
        " ".join(context.args)
        if context.args
        else (
            "Find 5 potential leads — founders or heads of growth at marketing agencies "
            "or SaaS companies with 10-50 employees. Research each one, draft a personalized "
            "LinkedIn connection message, and ask for approval before sending."
        )
    )
    await _start_task(task, "prospect", update)


async def cmd_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    task = (
        "Check Gmail for new unread business emails. Classify each one. "
        "For leads or inbound inquiries, research the sender, draft a reply, "
        "and ask for approval before sending. Send me a summary when done."
    )
    await _start_task(task, "inbox", update)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _current_task and not _current_task.done():
        await update.message.reply_text("Agent is running a task.")
    else:
        await update.message.reply_text("Agent is idle. Send a task to start.")


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global _current_task
    if _current_task and not _current_task.done():
        _current_task.cancel()
        await update.message.reply_text("Task cancelled.")
    else:
        await update.message.reply_text("No task running.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Any plain text message becomes a custom agent task.
    If the post scheduler is waiting for an edit, resolve it first.
    """
    task = update.message.text.strip()
    if not task:
        return
    # If post scheduler is waiting for an edited post, resolve it
    if resolve_edit(task):
        return
    await _start_task(task, "auto", update)


def register_handlers(app: Application) -> None:
    """Register all command and message handlers on the Telegram app."""
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("prospect", cmd_prospect))
    app.add_handler(CommandHandler("inbox", cmd_inbox))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("stop", cmd_stop))
    # Any non-command text → custom task
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
