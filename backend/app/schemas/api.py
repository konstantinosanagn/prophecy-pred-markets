"""Pydantic models for request/response validation."""

from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, constr, validator

from app.db.models import (
    ConfidenceLevel,
    Horizon,
    StrategyPreset,
)


class Signal(BaseModel):
    """Comprehensive trading signal with probabilities, edge, Kelly sizing, and recommendations."""

    # Beliefs
    market_prob: float = Field(
        ..., ge=0.0, le=1.0, description="p_mkt (implied by Polymarket price)"
    )
    model_prob: float = Field(
        ..., ge=0.0, le=1.0, description="p_model (posterior after news/analysis)"
    )
    edge_pct: float = Field(..., description="model_prob - market_prob (in probability points)")

    # Value & sizing
    expected_value_per_dollar: float = Field(..., description="Same as edge_pct in a $1 binary")
    kelly_fraction_yes: float = Field(
        ..., description="Unconstrained Kelly stake on YES in [0,1] (can be negative)"
    )
    kelly_fraction_no: float = Field(
        ..., description="Unconstrained Kelly stake on NO in [0,1] (can be negative)"
    )

    # Uncertainty / confidence
    confidence_level: ConfidenceLevel = Field(
        ..., description="Confidence level: low, medium, or high"
    )
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score in [0,1]")

    # Action & targets
    recommended_action: Literal["buy_yes", "buy_no", "reduce_yes", "reduce_no", "hold"] = Field(
        ..., description="Recommended trading action"
    )
    recommended_size_fraction: float = Field(
        ..., ge=0.0, le=1.0, description="Final, capped fraction, e.g. max 0.15"
    )
    target_take_profit_prob: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Take profit if market_prob >= this value"
    )
    target_stop_loss_prob: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Stop out if market_prob <= this value"
    )

    # Metadata
    horizon: Horizon = Field(..., description="Time horizon: intraday, 24h, or to_resolution")
    rationale_short: Optional[str] = Field(None, description="One-line explanation")
    rationale_long: Optional[str] = Field(None, description="Paragraph explanation (optional)")


class AnalysisConfiguration(BaseModel):
    """Configuration options for analysis agents and behavior."""

    use_tavily_prompt_agent: bool = Field(
        True, description="Use Tavily prompt agent (if False, use fallback queries)"
    )
    use_news_summary_agent: bool = Field(
        True, description="Use news summary agent (if False, use fallback summary)"
    )
    max_articles: int = Field(
        15, ge=5, le=30, description="Maximum number of articles to include in analysis"
    )
    max_articles_per_query: int = Field(
        8, ge=5, le=12, description="Maximum results per Tavily search query"
    )
    min_confidence: ConfidenceLevel = Field(
        "medium", description="Minimum confidence level for trading signals"
    )
    enable_sentiment_analysis: bool = Field(
        True, description="Enable sentiment analysis on articles"
    )


class AnalyzeRequest(BaseModel):
    """Request model for /api/analyze endpoint."""

    market_url: HttpUrl = Field(..., description="Polymarket event or market URL")
    selected_market_slug: Optional[str] = Field(
        None, description="Selected market slug when multiple markets exist"
    )
    horizon: Optional[Horizon] = Field("24h", description="Analysis time horizon")
    strategy_preset: Optional[StrategyPreset] = Field(
        "Balanced", description="Strategy risk preset"
    )
    strategy_params: Optional[dict[str, Any]] = Field(
        None, description="Optional strategy parameter overrides"
    )
    configuration: Optional[AnalysisConfiguration] = Field(
        None, description="Analysis configuration options"
    )

    @validator("market_url")
    def validate_polymarket_url(cls, v: HttpUrl) -> HttpUrl:
        """Validate that URL is a Polymarket URL."""
        url_str = str(v)
        if "polymarket.com" not in url_str.lower():
            raise ValueError("URL must be from polymarket.com domain")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "market_url": "https://polymarket.com/event/fed-decision-in-december",
                "selected_market_slug": None,
                "horizon": "24h",
                "strategy_preset": "Balanced",
            }
        }


class StrategyParamsModel(BaseModel):
    """Strategy parameters model."""

    min_edge_pct: float = Field(..., ge=0.0, le=1.0, description="Minimum edge percentage")
    min_confidence: ConfidenceLevel = Field(..., description="Minimum confidence level")
    max_capital_pct: float = Field(..., ge=0.0, le=1.0, description="Maximum capital percentage")


class MarketSelectionResponse(BaseModel):
    """Response when market selection is required."""

    requires_market_selection: Literal[True] = True
    event_context: dict[str, Any] = Field(..., description="Event context for UI")
    market_options: list[dict[str, Any]] = Field(..., description="Available market options")


class AnalyzeResponse(BaseModel):
    """Response model for /api/analyze endpoint."""

    run_id: str = Field(..., description="Unique run identifier")
    market_snapshot: dict[str, Any] = Field(..., description="Market state snapshot")
    event_context: dict[str, Any] = Field(..., description="Event context")
    news_context: dict[str, Any] = Field(..., description="News aggregation context")
    signal: dict[str, Any] = Field(..., description="Generated trading signal")
    decision: dict[str, Any] = Field(..., description="Trading decision")
    report: dict[str, Any] = Field(..., description="Analysis report")
    strategy_preset: StrategyPreset = Field(..., description="Strategy preset used")
    strategy_params: dict[str, Any] = Field(..., description="Strategy parameters used")
    horizon: Horizon = Field(..., description="Analysis horizon")
    snapshot: Optional[dict[str, Any]] = Field(None, description="Persisted snapshot metadata")


class RunRequest(BaseModel):
    """Request model for fetching runs."""

    market_id: constr(min_length=1) = Field(..., description="MongoDB ObjectId for market")


class RunResponse(BaseModel):
    """Response model for run endpoints."""

    market_id: str = Field(..., description="Market ID")
    runs: list[dict[str, Any]] = Field(..., description="List of runs for the market")


class SingleRunResponse(BaseModel):
    """Response model for single run endpoint."""

    run: dict[str, Any] = Field(..., description="Run document")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    message: str = Field(..., description="Status message")
    checks: Optional[dict[str, Any]] = Field(None, description="Dependency health checks")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error message")
    request_id: Optional[str] = Field(None, description="Request identifier for tracing")


class ReportSection(BaseModel):
    """Structured report section with AI-generated narrative fields."""

    headline: str = Field(
        ...,
        description="1 sentence, punchy headline mentioning model vs market if relevant",
    )
    thesis: str = Field(
        ..., description="3-5 sentences tying together market context, news, and model edge"
    )
    bull_case: List[str] = Field(..., description="2-4 short bullet points for bullish case")
    bear_case: List[str] = Field(..., description="2-4 short bullet points for bearish case")
    key_risks: List[str] = Field(..., description="2-4 short bullet points for key risks")
    execution_notes: str = Field(
        ..., description="2-3 sentences on sizing, TP/SL usage, and when to re-check"
    )
