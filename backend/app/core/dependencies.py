"""FastAPI dependency injection for service clients."""

from __future__ import annotations

from app.services.openai_client import OpenAIClient, get_openai_client
from app.services.polymarket_client import PolymarketClient, get_polymarket_client


async def get_polymarket_client_dep() -> PolymarketClient:
    """FastAPI dependency for PolymarketClient."""
    return get_polymarket_client()


async def get_openai_client_dep() -> OpenAIClient:
    """FastAPI dependency for OpenAIClient."""
    return get_openai_client()
