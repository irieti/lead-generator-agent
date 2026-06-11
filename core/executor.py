"""
Tool executor.

Claude returns tool_use blocks with a name and input dict.
This module routes each call to the correct implementation.
"""
from __future__ import annotations

import json
from typing import Any

from tools.linkedin import search_linkedin, get_linkedin_profile, send_linkedin_invite
from tools.gmail import read_gmail, send_gmail
from tools.sheets import read_sheet, write_sheet
from tools.telegram import telegram_ask, telegram_notify
from tools.web_search import web_search
from tools.linkedin_post import post_linkedin
from core.logging import get_logger

logger = get_logger("executor")


async def execute_tool(name: str, inputs: dict[str, Any]) -> str:
    """
    Execute a tool by name with given inputs.
    Returns a JSON string — this goes back to Claude as the tool result.
    """
    logger.info("tool.execute", tool=name, inputs=inputs)

    try:
        result: Any

        if name == "search_linkedin":
            result = await search_linkedin(
                query=inputs["query"],
                limit=inputs.get("limit", 10),
            )
        elif name == "get_linkedin_profile":
            result = await get_linkedin_profile(profile_url=inputs["profile_url"])

        elif name == "send_linkedin_invite":
            result = await send_linkedin_invite(
                profile_url=inputs["profile_url"],
                message=inputs["message"],
            )
        elif name == "web_search":
            result = await web_search(query=inputs["query"])

        elif name == "read_gmail":
            result = await read_gmail(
                query=inputs.get("query", "is:unread"),
                limit=inputs.get("limit", 10),
            )
        elif name == "send_gmail":
            result = await send_gmail(
                to=inputs["to"],
                subject=inputs["subject"],
                body=inputs["body"],
                reply_to_thread_id=inputs.get("reply_to_thread_id"),
            )
        elif name == "read_sheet":
            result = await read_sheet(
                worksheet=inputs.get("worksheet", "Leads"),
                search_value=inputs.get("search_value"),
            )
        elif name == "write_sheet":
            result = await write_sheet(
                row=inputs["row"],
                worksheet=inputs.get("worksheet", "Leads"),
            )
        elif name == "telegram_ask":
            result = await telegram_ask(
                message=inputs["message"],
                options=inputs.get("options", ["Approve", "Reject"]),
            )
        elif name == "telegram_notify":
            result = await telegram_notify(message=inputs["message"])

        elif name == "post_linkedin":
            result = await post_linkedin(text=inputs["text"])

        else:
            result = {"error": f"Unknown tool: {name}"}

        logger.info("tool.done", tool=name, result_keys=list(result.keys()) if isinstance(result, dict) else "scalar")
        return json.dumps(result)

    except Exception as e:
        logger.error("tool.error", tool=name, error=str(e))
        return json.dumps({"error": str(e)})
