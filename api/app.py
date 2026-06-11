"""
AGENT//OS — FastAPI entry point

Routes:
  POST /agent/run        — run agent, stream SSE events back
  POST /agent/run/sync   — run agent, wait for completion, return JSON
  GET  /health           — health check

The SSE stream lets you watch the agent work in real time.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.agent import run_agent
from core.config import settings
from core.logging import get_logger, setup_logging
from core.scheduler import build_scheduler
from core.post_scheduler import build_post_scheduler
from tools.telegram import get_app as get_telegram_app
from bot.receiver import register_handlers

setup_logging()
logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Telegram bot — handles both approval callbacks and incoming task messages
    tg = get_telegram_app()
    register_handlers(tg)
    await tg.initialize()
    await tg.start()
    await tg.updater.start_polling(drop_pending_updates=True)
    logger.info("telegram.polling_started")

    # Lead scheduler
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("scheduler.started")

    # Post scheduler
    post_scheduler = build_post_scheduler()
    post_scheduler.start()
    logger.info("post_scheduler.started")

    yield

    scheduler.shutdown(wait=False)
    post_scheduler.shutdown(wait=False)
    logger.info("schedulers.stopped")
    await tg.updater.stop()
    await tg.stop()
    await tg.shutdown()
    logger.info("telegram.stopped")


app = FastAPI(
    title="AGENT//OS",
    description="Autonomous agent — LinkedIn, Gmail, Sheets, Telegram",
    version="1.0.0",
    lifespan=lifespan,
)


class RunRequest(BaseModel):
    task: str = Field(..., min_length=5, description="What the agent should do")
    mode: str = Field(
        "auto",
        description="PROSPECT | INBOX | RESEARCH | auto",
        pattern="^(prospect|inbox|research|auto)$",
    )
    max_iterations: int = Field(50, ge=1, le=100)


# ── Streaming endpoint (SSE) ──────────────────────────────────────────────────

@app.post("/agent/run")
async def run_agent_stream(request: RunRequest) -> StreamingResponse:
    """
    Run the agent and stream Server-Sent Events back.
    Each event is a JSON object with a `type` field.

    Example curl:
        curl -N -X POST http://localhost:8000/agent/run \\
          -H "Content-Type: application/json" \\
          -d '{"task": "Find 5 AI startup founders in Lisbon and draft outreach", "mode": "prospect"}'
    """
    async def event_stream():
        async for event in run_agent(
            task=request.task,
            mode=request.mode,
            max_iterations=request.max_iterations,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Sync endpoint (waits for completion) ─────────────────────────────────────

@app.post("/agent/run/sync")
async def run_agent_sync(request: RunRequest) -> dict:
    """
    Run the agent and wait for completion. Returns all events as a list.
    Use for testing; prefer /agent/run for production.
    """
    events = []
    async for event in run_agent(
        task=request.task,
        mode=request.mode,
        max_iterations=request.max_iterations,
    ):
        events.append(event)
        if event["type"] in ("done", "error"):
            break

    final = next((e for e in reversed(events) if e["type"] == "done"), None)
    return {
        "output": final["output"] if final else "",
        "iterations": final["iterations"] if final else 0,
        "events": events,
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "AGENT//OS", "version": "1.0.0"}
