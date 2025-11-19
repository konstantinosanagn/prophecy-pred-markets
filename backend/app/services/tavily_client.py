"""Tavily API client with caching and retry logic."""

from __future__ import annotations

from typing import Any, Dict

import aiohttp
from aiohttp import ClientTimeout

from app.config import settings
from app.core.cache import tavily_cache
from app.core.logging_config import get_logger
from app.core.resilience import tavily_circuit, with_async_retry
from app.schemas.tavily import TavilySearchResult

logger = get_logger(__name__)


TAVILY_API_URL = "https://api.tavily.com/search"
TAVILY_API_KEY = settings.tavily_api_key


async def _search_news_impl_async(
    query: str, max_results: int = 5, search_depth: str | None = None
) -> Dict[str, Any]:
    """Internal async implementation of search_news with aiohttp.

    Note: search_depth parameter is not currently supported by Tavily API.
    It's included in the signature for future compatibility but will be ignored.
    """
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY is not configured")

    logger.debug(
        "Searching Tavily (async)",
        query=query,
        max_results=max_results,
        search_depth=search_depth,
    )

    # Build request payload
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": max_results,
        "include_answer": True,
        "include_raw_content": False,
    }

    # Note: Tavily API may support search_depth in the future
    # For now, we log if it's requested but don't send it
    if search_depth:
        logger.debug(
            "search_depth parameter requested but not yet supported by Tavily API",
            search_depth=search_depth,
        )

    timeout_obj = ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout_obj) as session:
        async with session.post(
            TAVILY_API_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
        ) as response:
            response.raise_for_status()
            return await response.json()


async def search_news(
    query: str, max_results: int = 5, search_depth: str | None = None
) -> Dict[str, Any]:
    """Call Tavily's search API with caching, retry, and circuit breaker protection (async).

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)
        search_depth: Search depth ("basic" or "advanced") - not yet supported by Tavily API

    Returns:
        Dictionary with answer and articles (for backward compatibility with TypedDict usage)
        Articles are Pydantic models converted to dicts
    """
    if not TAVILY_API_KEY:
        # Fail soft: let the caller fall back to placeholder content.
        logger.warning("TAVILY_API_KEY not configured")
        return {"answer": "", "articles": []}

    # Create cache key (include search_depth for future cache differentiation)
    cache_key = f"tavily:{query}:{max_results}:{search_depth or 'basic'}"

    # Try cache first
    cached_result = tavily_cache.get(cache_key)
    if cached_result is not None:
        logger.debug("Cache hit for Tavily (async)", query=query)
        # Convert cached Pydantic models to dicts if needed
        if isinstance(cached_result, TavilySearchResult):
            return {
                "answer": cached_result.answer,
                "articles": [article.model_dump() for article in cached_result.articles],
            }
        # Handle old dict format (backward compatibility)
        elif isinstance(cached_result, dict):
            return cached_result
        # Fallback: try to convert if it's a Pydantic model
        elif hasattr(cached_result, "model_dump"):
            return {
                "answer": getattr(cached_result, "answer", ""),
                "articles": [
                    a.model_dump() if hasattr(a, "model_dump") else a
                    for a in getattr(cached_result, "articles", [])
                ],
            }
        return cached_result

    # Check circuit breaker
    if not tavily_circuit.can_attempt():
        logger.warning("Circuit breaker open for Tavily (async)", query=query)
        return {"answer": "", "articles": []}

    # Cache miss - fetch with retry and circuit breaker
    try:
        data = await with_async_retry(
            _search_news_impl_async,
            max_attempts=3,
            base_delay=1.0,
            max_delay=20.0,
            query=query,
            max_results=max_results,
            search_depth=search_depth,
        )

        # Process results using Pydantic schemas
        result = TavilySearchResult.from_api_response(data)

        # Cache successful result (cache the Pydantic model)
        tavily_cache.set(cache_key, result)
        tavily_circuit.record_success()
        logger.debug(
            "Cache miss - fetched and cached (async)",
            query=query,
            articles_count=len(result.articles),
        )

        # Return as dict for backward compatibility
        return {
            "answer": result.answer,
            "articles": [article.model_dump() for article in result.articles],
        }

    except Exception as e:
        tavily_circuit.record_failure()
        # Network / API error – don't crash the graph, just return empty.
        logger.warning("Failed to search Tavily (async)", query=query, error=str(e), exc_info=True)
        return {"answer": "", "articles": []}
