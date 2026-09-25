"""Fetcher: Tavily/Brave search + httpx static fetch with robots.txt compliance."""
from __future__ import annotations

import asyncio
import hashlib
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from loguru import logger

from api.config.settings import settings

_robots_cache: dict[str, tuple[RobotFileParser, float]] = {}
ROBOTS_TTL = 86400  # 24 hours
USER_AGENT = "ScoutIQ/1.0 (+https://scoutiq.dev/bot)"


async def is_allowed(url: str) -> bool:
    """Check robots.txt for this URL (cached 24h)."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = f"{base}/robots.txt"
    now = time.time()

    cached = _robots_cache.get(base)
    if cached and now - cached[1] < ROBOTS_TTL:
        rp = cached[0]
    else:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(robots_url, headers={"User-Agent": USER_AGENT})
                rp.parse(resp.text.splitlines())
        except Exception:
            rp.allow_all = True
        _robots_cache[base] = (rp, now)

    return rp.can_fetch(USER_AGENT, url)


async def search_tavily(query: str, max_results: int = 10) -> list[dict]:
    """Search via Tavily API."""
    if not settings.tavily_api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": settings.tavily_api_key, "query": query, "max_results": max_results},
            )
            data = resp.json()
            return data.get("results", [])
    except Exception as e:
        logger.warning(f"Tavily search failed: {e}")
        return []


async def search_brave(query: str, max_results: int = 10) -> list[dict]:
    """Search via Brave Search API."""
    if not settings.brave_api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": max_results},
                headers={"Accept": "application/json", "X-Subscription-Token": settings.brave_api_key},
            )
            data = resp.json()
            return data.get("web", {}).get("results", [])
    except Exception as e:
        logger.warning(f"Brave search failed: {e}")
        return []


async def fetch_url(url: str) -> dict | None:
    """Fetch a URL and return {url, html, text, content_hash, fetched_at}."""
    if not await is_allowed(url):
        logger.warning(f"robots.txt disallows: {url}")
        return None
    try:
        async with httpx.AsyncClient(
            timeout=30,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                return None
            html = resp.text
            content_hash = hashlib.sha256(html.encode()).hexdigest()
            # Extract text via trafilatura
            try:
                import trafilatura
                text = trafilatura.extract(html) or ""
            except Exception:
                text = html[:5000]
            return {
                "url": url,
                "html": html,
                "text": text,
                "content_hash": content_hash,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "http_status": resp.status_code,
                "size_bytes": len(html.encode()),
            }
    except Exception as e:
        logger.warning(f"Fetch failed {url}: {e}")
        return None


async def fetch_sources(
    requirement_spec: dict,
    config: dict,
    run_id: str,
    db: Any,
) -> list[dict]:
    """Discover and fetch sources for a requirement spec."""
    entity_type = requirement_spec.get("entity_type", "")
    filters = requirement_spec.get("filters", {})
    query_parts = [entity_type]
    for k, v in filters.items():
        if isinstance(v, str):
            query_parts.append(v)
    query = " ".join(query_parts)

    results = await search_tavily(query, max_results=config.get("max_pages", 10))
    if not results:
        results = await search_brave(query, max_results=config.get("max_pages", 10))

    fetched = []
    sem = asyncio.Semaphore(5)  # max 5 concurrent fetches

    async def _fetch(r: dict) -> None:
        url = r.get("url", "")
        if not url:
            return
        async with sem:
            page = await fetch_url(url)
            if page:
                fetched.append(page)

    await asyncio.gather(*[_fetch(r) for r in results])
    return fetched
