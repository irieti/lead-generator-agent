"""
Web search tool using DuckDuckGo (no API key needed).
Swap for Tavily or Serper if you need better results.
"""
from __future__ import annotations

import httpx
from typing import Any

from core.logging import get_logger

logger = get_logger("tools.web_search")

DDGO_URL = "https://api.duckduckgo.com/"


async def web_search(query: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                DDGO_URL,
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []

        # Abstract (main result)
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", ""),
                "snippet": data["AbstractText"],
                "url": data.get("AbstractURL", ""),
            })

        # Related topics
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:80],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                })

        logger.info("web_search.done", query=query, results=len(results))
        return {"results": results, "count": len(results), "query": query}

    except Exception as e:
        logger.error("web_search.error", query=query, error=str(e))
        return {"error": str(e), "results": []}
