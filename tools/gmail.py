"""
Gmail tool using the Gmail MCP server.
Connects via MCP protocol — no manual OAuth flow needed beyond initial setup.
"""
from __future__ import annotations

import asyncio
import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from core.logging import get_logger

logger = get_logger("tools.gmail")

# Gmail MCP server — runs as a subprocess
GMAIL_MCP_PARAMS = StdioServerParameters(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-gmail"],
    env=None,
)


async def _call_gmail_mcp(tool_name: str, arguments: dict) -> Any:
    """Connect to Gmail MCP server, call a tool, return result."""
    async with stdio_client(GMAIL_MCP_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            # Extract text content from MCP result
            if result.content:
                for block in result.content:
                    if hasattr(block, "text"):
                        try:
                            return json.loads(block.text)
                        except json.JSONDecodeError:
                            return {"text": block.text}
            return {}


async def read_gmail(query: str = "is:unread", limit: int = 10) -> dict[str, Any]:
    """Read emails matching a Gmail search query."""
    try:
        result = await _call_gmail_mcp(
            "gmail_search_emails",
            {"query": query, "maxResults": limit},
        )
        emails = result.get("messages", [])
        logger.info("gmail.read_done", query=query, count=len(emails))
        return {"emails": emails, "count": len(emails)}
    except Exception as e:
        logger.error("gmail.read_error", error=str(e))
        return {"error": str(e), "emails": []}


async def send_gmail(
    to: str,
    subject: str,
    body: str,
    reply_to_thread_id: str | None = None,
) -> dict[str, Any]:
    """Send an email via Gmail MCP."""
    try:
        payload: dict[str, Any] = {
            "to": to,
            "subject": subject,
            "body": body,
        }
        if reply_to_thread_id:
            payload["threadId"] = reply_to_thread_id

        result = await _call_gmail_mcp("gmail_send_email", payload)
        logger.info("gmail.sent", to=to, subject=subject)
        return {"success": True, "message_id": result.get("id", "")}
    except Exception as e:
        logger.error("gmail.send_error", error=str(e))
        return {"error": str(e)}
