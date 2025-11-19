"""Schemas package for request/response validation."""

# API request/response schemas
from app.schemas.api import (
    AnalyzeRequest,
    AnalyzeResponse,
    ErrorResponse,
    HealthResponse,
    MarketSelectionResponse,
    RunRequest,
    RunResponse,
    SingleRunResponse,
    StrategyParamsModel,
)

# Polymarket API schemas
from app.schemas.polymarket import ClobReward, Event, Market, Tag

__all__ = [
    # API schemas
    "AnalyzeRequest",
    "AnalyzeResponse",
    "ErrorResponse",
    "HealthResponse",
    "MarketSelectionResponse",
    "RunRequest",
    "RunResponse",
    "SingleRunResponse",
    "StrategyParamsModel",
    # Polymarket schemas
    "ClobReward",
    "Event",
    "Market",
    "Tag",
]
