"""
Telegram tool.

telegram_ask  — sends a message with inline buttons and BLOCKS until the user responds.
telegram_notify — fire-and-forget notification.

The approval gate is the core of the human-in-the-loop pattern.
"""
from __future__ import annotations

import asyncio
from typing import Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from core.config import settings
from core.logging import get_logger

logger = get_logger("tools.telegram")

# Pending approvals: run_id → asyncio.Future
_pending: dict[str, asyncio.Future] = {}

# Singleton bot app (started once at server startup)
_app: Application | None = None


def get_app() -> Application:
    global _app
    if _app is None:
        _app = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .build()
        )
        _app.add_handler(CallbackQueryHandler(_callback_handler))
    return _app


async def _callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button taps. Resolves the waiting Future."""
    query = update.callback_query
    await query.answer()

    data = query.data  # format: "approval:{approval_id}:{value}"
    parts = data.split(":", 2)
    if len(parts) != 3 or parts[0] != "approval":
        return

    _, approval_id, value = parts
    future = _pending.get(approval_id)
    if future and not future.done():
        future.set_result(value)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"✅ Response recorded: *{value}*", parse_mode="Markdown")

    logger.info("telegram.callback_resolved", approval_id=approval_id, value=value)


async def telegram_ask(
    message: str,
    options: list[str] | None = None,
    approval_id: str | None = None,
) -> dict[str, Any]:
    """
    Send a message with inline buttons and wait for the user to tap one.
    Blocks until response or timeout.
    Returns {"response": "Approve"} or {"response": "Reject"} or {"response": "timeout"}.
    """
    import uuid

    if options is None:
        options = ["Approve", "Reject"]

    if approval_id is None:
        approval_id = str(uuid.uuid4())[:8]

    # Build keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(opt, callback_data=f"approval:{approval_id}:{opt}")]
        for opt in options
    ])

    bot = Bot(token=settings.telegram_bot_token)
    await bot.send_message(
        chat_id=settings.telegram_chat_id,
        text=message,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

    # Register future and wait
    loop = asyncio.get_event_loop()
    future: asyncio.Future = loop.create_future()
    _pending[approval_id] = future

    logger.info("telegram.waiting_for_approval", approval_id=approval_id)

    try:
        response = await asyncio.wait_for(future, timeout=settings.telegram_approval_timeout)
        logger.info("telegram.approval_received", approval_id=approval_id, response=response)
        return {"response": response, "approved": response.lower() == "approve"}
    except asyncio.TimeoutError:
        logger.warning("telegram.approval_timeout", approval_id=approval_id)
        await bot.send_message(
            chat_id=settings.telegram_chat_id,
            text=f"⏱ Approval `{approval_id}` timed out — skipping.",
            parse_mode="Markdown",
        )
        return {"response": "timeout", "approved": False}
    finally:
        _pending.pop(approval_id, None)


async def telegram_notify(message: str) -> dict[str, Any]:
    """Fire-and-forget notification. Does not wait for response."""
    try:
        bot = Bot(token=settings.telegram_bot_token)
        await bot.send_message(
            chat_id=settings.telegram_chat_id,
            text=message,
            parse_mode="Markdown",
        )
        logger.info("telegram.notified")
        return {"success": True}
    except Exception as e:
        logger.error("telegram.notify_error", error=str(e))
        return {"error": str(e)}
