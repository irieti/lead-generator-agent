"""
LinkedIn post tool.

Strategy:
  1. Try official LinkedIn API via MCP server (FilippTrigub/linkedin-mcp)
  2. Fall back to Playwright if MCP not configured (no client_id set)

The MCP route is safer — uses the official Share on LinkedIn API.
The Playwright route works but carries account risk.
"""

from __future__ import annotations

import json
from typing import Any

from core.config import settings
from core.logging import get_logger

logger = get_logger("tools.linkedin_post")


async def post_linkedin(text: str) -> dict[str, Any]:
    if settings.linkedin_client_id and settings.linkedin_access_token:
        return await _post_via_mcp(text)
    else:
        logger.warning(
            "linkedin_post.no_api_credentials",
            msg="LINKEDIN_CLIENT_ID not set — falling back to Playwright",
        )
        return await _post_via_playwright(text)


async def _post_via_mcp(text: str) -> dict[str, Any]:
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(
            command="linkedin-mcp",
            args=[],
            env={
                "LINKEDIN_CLIENT_ID": settings.linkedin_client_id,
                "LINKEDIN_CLIENT_SECRET": settings.linkedin_client_secret,
                "LINKEDIN_REDIRECT_URI": settings.linkedin_redirect_uri,
                "LINKEDIN_ACCESS_TOKEN": settings.linkedin_access_token,
            },
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "create_text_post",
                    {"text": text, "visibility": "PUBLIC"},
                )
                if result.content:
                    for block in result.content:
                        if hasattr(block, "text"):
                            data = (
                                json.loads(block.text)
                                if block.text.startswith("{")
                                else {"text": block.text}
                            )
                            logger.info("linkedin_post.mcp_success")
                            return {"success": True, "method": "mcp", "response": data}

        return {"success": True, "method": "mcp"}

    except Exception as e:
        logger.error("linkedin_post.mcp_error", error=str(e))
        logger.info("linkedin_post.falling_back_to_playwright")
        return await _post_via_playwright(text)


async def _post_via_playwright(text: str) -> dict[str, Any]:
    import asyncio
    from playwright.async_api import async_playwright

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=settings.linkedin_headless,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

            # Login
            await page.goto("https://www.linkedin.com/login")
            await page.fill("#username", settings.linkedin_email)
            await page.fill("#password", settings.linkedin_password)
            await page.click('[type="submit"]')
            await page.wait_for_url("**/feed/**", timeout=15000)

            # Open post composer
            await page.goto("https://www.linkedin.com/feed/")
            await asyncio.sleep(2)

            start_post = await page.query_selector(
                '[data-control-name="share.sharebox_text"]'
            )
            if not start_post:
                start_post = await page.query_selector(".share-box-feed-entry__trigger")
            if start_post:
                await start_post.click()
                await asyncio.sleep(1)

            # Type post content
            editor = await page.query_selector(".ql-editor")
            if not editor:
                editor = await page.query_selector('[contenteditable="true"]')
            if editor:
                await editor.fill(text)
                await asyncio.sleep(1)

            # Submit
            submit_btn = await page.query_selector(
                'button[data-control-name="share.post"]'
            )
            if not submit_btn:
                submit_btn = await page.query_selector(".share-actions__primary-action")
            if submit_btn:
                await submit_btn.click()
                await asyncio.sleep(2)
                logger.info("linkedin_post.playwright_success")
                await browser.close()
                return {"success": True, "method": "playwright"}

            await browser.close()
            return {"error": "Could not find post submit button"}

    except Exception as e:
        logger.error("linkedin_post.playwright_error", error=str(e))
        return {"error": str(e)}
