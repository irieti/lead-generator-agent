"""
Google Sheets tool using the Google Sheets MCP server.
"""
from __future__ import annotations

import json
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from core.config import settings
from core.logging import get_logger

logger = get_logger("tools.sheets")

SHEETS_MCP_PARAMS = StdioServerParameters(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-google-sheets"],
    env={"GOOGLE_SERVICE_ACCOUNT_JSON": settings.google_service_account_json},
)

SHEET_HEADERS = [
    "date", "name", "company", "role", "linkedin_url", "email",
    "source", "score", "status", "notes", "outreach_sent", "outreach_type",
]


async def _call_sheets_mcp(tool_name: str, arguments: dict) -> Any:
    async with stdio_client(SHEETS_MCP_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            if result.content:
                for block in result.content:
                    if hasattr(block, "text"):
                        try:
                            return json.loads(block.text)
                        except json.JSONDecodeError:
                            return {"text": block.text}
            return {}


async def read_sheet(
    worksheet: str = "Leads",
    search_value: str | None = None,
) -> dict[str, Any]:
    try:
        result = await _call_sheets_mcp(
            "sheets_get_values",
            {
                "spreadsheetId": settings.google_sheet_id,
                "range": f"{worksheet}!A:Z",
            },
        )
        rows = result.get("values", [])

        if search_value and rows:
            headers = rows[0] if rows else []
            data_rows = rows[1:]
            matches = [
                dict(zip(headers, row))
                for row in data_rows
                if any(search_value.lower() in str(cell).lower() for cell in row)
            ]
            return {"rows": matches, "count": len(matches)}

        if rows:
            headers = rows[0]
            data = [dict(zip(headers, row)) for row in rows[1:]]
            return {"rows": data, "count": len(data)}

        return {"rows": [], "count": 0}

    except Exception as e:
        logger.error("sheets.read_error", error=str(e))
        return {"error": str(e), "rows": []}


async def write_sheet(
    row: dict[str, Any],
    worksheet: str = "Leads",
) -> dict[str, Any]:
    from datetime import datetime

    try:
        # Ensure date
        if "date" not in row:
            row["date"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

        # Read existing to check headers
        existing = await _call_sheets_mcp(
            "sheets_get_values",
            {
                "spreadsheetId": settings.google_sheet_id,
                "range": f"{worksheet}!A1:Z1",
            },
        )
        existing_headers = existing.get("values", [[]])[0]

        if not existing_headers:
            # Write headers first
            await _call_sheets_mcp(
                "sheets_update_values",
                {
                    "spreadsheetId": settings.google_sheet_id,
                    "range": f"{worksheet}!A1",
                    "values": [SHEET_HEADERS],
                },
            )
            existing_headers = SHEET_HEADERS

        # Build row in header order
        ordered_row = [str(row.get(h, "")) for h in existing_headers]

        result = await _call_sheets_mcp(
            "sheets_append_values",
            {
                "spreadsheetId": settings.google_sheet_id,
                "range": f"{worksheet}!A:Z",
                "values": [ordered_row],
            },
        )

        logger.info("sheets.row_written", worksheet=worksheet, name=row.get("name", ""))
        return {"success": True}

    except Exception as e:
        logger.error("sheets.write_error", error=str(e))
        return {"error": str(e)}
