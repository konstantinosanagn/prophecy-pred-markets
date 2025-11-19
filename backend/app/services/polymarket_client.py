"""Polymarket API client with caching, retry, and circuit breaker."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.core.polymarket_utils import (
    fetch_json_async,
    fetch_order_book_async,
    get_event_and_markets_by_slug,
)


class PolymarketClient:
    """Client for interacting with Polymarket APIs.

    Provides async methods with built-in caching, retry logic, and circuit breaker protection.
    """

    async def get_event_and_markets(
        self, slug: str
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Get event and markets by slug.

        Args:
            slug: Market or event slug

        Returns:
            Tuple of (event_dict, markets_list)
        """
        return await get_event_and_markets_by_slug(slug)

    async def fetch_order_book(self, token_id: str) -> Dict[str, Any]:
        """Fetch order book for a token.

        Args:
            token_id: CLOB token ID

        Returns:
            Order book dictionary with bids, asks, best_bid, best_ask
        """
        return await fetch_order_book_async(token_id)

    async def fetch_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Fetch JSON from a URL.

        Args:
            url: URL to fetch
            params: Optional query parameters

        Returns:
            Parsed JSON response
        """
        return await fetch_json_async(url, params=params)


# Module-level singleton instance
_polymarket_client: Optional[PolymarketClient] = None


def get_polymarket_client() -> PolymarketClient:
    """Get the singleton PolymarketClient instance."""
    global _polymarket_client
    if _polymarket_client is None:
        _polymarket_client = PolymarketClient()
    return _polymarket_client
