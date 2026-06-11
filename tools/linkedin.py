"""
LinkedIn tool using Playwright browser automation.
Logs in as the user and performs actions (search, profile fetch, send invite).
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from core.config import settings
from core.logging import get_logger

logger = get_logger("tools.linkedin")

_browser: Browser | None = None
_context: BrowserContext | None = None
_invite_count: int = 0  # daily counter


async def _get_context() -> BrowserContext:
    global _browser, _context
    if _context is None:
        playwright = await async_playwright().start()
        _browser = await playwright.chromium.launch(
            headless=settings.linkedin_headless,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        _context = await _browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        await _login(_context)
    return _context


async def _login(context: BrowserContext) -> None:
    page = await context.new_page()
    logger.info("linkedin.login_start")
    await page.goto("https://www.linkedin.com/login")
    await page.fill("#username", settings.linkedin_email)
    await page.fill("#password", settings.linkedin_password)
    await page.click('[type="submit"]')
    await page.wait_for_url("**/feed/**", timeout=15000)
    logger.info("linkedin.login_success")
    await page.close()


async def _random_delay() -> None:
    base = settings.linkedin_delay_between_actions
    await asyncio.sleep(base + (time.time() % 2))  # base + 0-2s jitter


async def search_linkedin(query: str, limit: int = 10) -> dict[str, Any]:
    context = await _get_context()
    page = await context.new_page()
    results = []

    try:
        encoded = query.replace(" ", "%20")
        await page.goto(
            f"https://www.linkedin.com/search/results/people/?keywords={encoded}&origin=GLOBAL_SEARCH_HEADER",
            wait_until="networkidle",
        )
        await _random_delay()

        cards = await page.query_selector_all(".reusable-search__result-container")
        for card in cards[:limit]:
            try:
                name_el = await card.query_selector(".entity-result__title-text a")
                headline_el = await card.query_selector(".entity-result__primary-subtitle")
                company_el = await card.query_selector(".entity-result__secondary-subtitle")
                url_el = await card.query_selector(".entity-result__title-text a")

                name = await name_el.inner_text() if name_el else ""
                headline = await headline_el.inner_text() if headline_el else ""
                company = await company_el.inner_text() if company_el else ""
                url = await url_el.get_attribute("href") if url_el else ""

                if name.strip():
                    results.append({
                        "name": name.strip(),
                        "headline": headline.strip(),
                        "company": company.strip(),
                        "profile_url": url.split("?")[0] if url else "",
                    })
            except Exception:
                continue

        logger.info("linkedin.search_done", query=query, results=len(results))
        return {"results": results, "count": len(results)}

    except Exception as e:
        logger.error("linkedin.search_error", error=str(e))
        return {"error": str(e), "results": []}
    finally:
        await page.close()


async def get_linkedin_profile(profile_url: str) -> dict[str, Any]:
    context = await _get_context()
    page = await context.new_page()

    try:
        await page.goto(profile_url, wait_until="networkidle")
        await _random_delay()

        name_el = await page.query_selector("h1.text-heading-xlarge")
        headline_el = await page.query_selector(".text-body-medium.break-words")
        location_el = await page.query_selector(".text-body-small.inline.t-black--light")
        about_el = await page.query_selector("#about ~ div .inline-show-more-text")
        company_els = await page.query_selector_all(".experience-item .t-bold span")

        name = await name_el.inner_text() if name_el else ""
        headline = await headline_el.inner_text() if headline_el else ""
        location = await location_el.inner_text() if location_el else ""
        about = await about_el.inner_text() if about_el else ""
        companies = [await el.inner_text() for el in company_els[:2]]

        logger.info("linkedin.profile_fetched", profile_url=profile_url)
        return {
            "name": name.strip(),
            "headline": headline.strip(),
            "location": location.strip(),
            "about": about.strip()[:500],
            "recent_companies": companies,
            "profile_url": profile_url,
        }

    except Exception as e:
        logger.error("linkedin.profile_error", error=str(e))
        return {"error": str(e)}
    finally:
        await page.close()


async def send_linkedin_invite(profile_url: str, message: str) -> dict[str, Any]:
    global _invite_count

    if _invite_count >= settings.linkedin_daily_invite_limit:
        return {
            "error": f"Daily invite limit reached ({settings.linkedin_daily_invite_limit}). Try again tomorrow."
        }

    if len(message) > 300:
        message = message[:297] + "..."

    context = await _get_context()
    page = await context.new_page()

    try:
        await page.goto(profile_url, wait_until="networkidle")
        await _random_delay()

        # Click Connect button
        connect_btn = await page.query_selector('button[aria-label*="Connect"]')
        if not connect_btn:
            # Try the More menu
            more_btn = await page.query_selector('button[aria-label*="More actions"]')
            if more_btn:
                await more_btn.click()
                await _random_delay()
                connect_btn = await page.query_selector('[aria-label*="Connect"]')

        if not connect_btn:
            return {"error": "Connect button not found — profile may already be connected"}

        await connect_btn.click()
        await _random_delay()

        # Add a note
        add_note_btn = await page.query_selector('button[aria-label="Add a note"]')
        if add_note_btn:
            await add_note_btn.click()
            await _random_delay()
            note_field = await page.query_selector("#custom-message")
            if note_field:
                await note_field.fill(message)
                await _random_delay()

        # Send
        send_btn = await page.query_selector('button[aria-label="Send invitation"]')
        if send_btn:
            await send_btn.click()
            _invite_count += 1
            logger.info(
                "linkedin.invite_sent",
                profile_url=profile_url,
                daily_count=_invite_count,
            )
            return {"success": True, "daily_invites_sent": _invite_count}
        else:
            return {"error": "Send button not found"}

    except Exception as e:
        logger.error("linkedin.invite_error", error=str(e))
        return {"error": str(e)}
    finally:
        await page.close()
