"""Phased analysis runner for background task execution."""

from __future__ import annotations

from app.agents.event_agent import run_event_agent
from app.agents.market_agent import run_market_agent
from app.agents.news_agent import run_news_agent
from app.agents.news_summary_agent import run_news_summary_agent
from app.agents.prob_agent import run_prob_agent
from app.agents.report_agent import run_report_agent
from app.agents.state import AgentState
from app.agents.strategy_agent import run_strategy_agent
from app.agents.tavily_prompt_agent import run_tavily_prompt_agent
from app.core.logging_config import get_logger
from app.schemas import AnalyzeRequest
from app.services.run_snapshot import (
    persist_run_snapshot_async,
    update_run_phase_async,
    update_run_with_event_and_market_async,
)

logger = get_logger(__name__)


async def run_analysis_for_run_id(run_id: str, req: AnalyzeRequest) -> None:
    """Run the analysis graph in phases, updating the run document as each phase completes."""
    try:
        # Initialize state
        config = req.configuration
        # Merge config min_confidence into strategy_params if provided
        strategy_params = req.strategy_params or {}
        if config and config.min_confidence:
            strategy_params = {**strategy_params, "min_confidence": config.min_confidence}

        state: AgentState = {
            "run_id": run_id,
            "market_url": str(req.market_url),
            "polymarket_url": str(req.market_url),
            "selected_market_slug": req.selected_market_slug,
            "horizon": req.horizon or "24h",
            "strategy_preset": req.strategy_preset or "Balanced",
            "strategy_params": strategy_params,
            # Configuration options
            "config": {
                "use_tavily_prompt_agent": config.use_tavily_prompt_agent if config else True,
                "use_news_summary_agent": config.use_news_summary_agent if config else True,
                "max_articles": config.max_articles if config else 15,
                "max_articles_per_query": config.max_articles_per_query if config else 8,
                "min_confidence": config.min_confidence if config else "medium",
                "enable_sentiment_analysis": config.enable_sentiment_analysis if config else True,
            }
            if config
            else {},
        }

        logger.info("Starting phased analysis", run_id=run_id)

        # PHASE 1: Market + Event
        logger.debug("Phase 1: Market and Event", run_id=run_id)
        state = await run_market_agent(state)
        state = await run_event_agent(state)

        # Check if market selection is required
        if state.get("requires_market_selection"):
            logger.info("Market selection required", run_id=run_id)
            # Update run with event context and market options (but not market snapshot)
            try:
                await update_run_phase_async(
                    run_id,
                    "market",
                    "done",  # Mark as done even though we need selection
                    {
                        "event_context": state.get("event_context", {}),
                        "market_options": state.get("market_options", []),
                    },
                )
            except Exception as db_error:
                logger.warning(
                    "Failed to update run document for market selection",
                    run_id=run_id,
                    error=str(db_error),
                    exc_info=True,
                )
            # Don't continue with other phases - user needs to select a market first
            return

        # Update run with market snapshot and event context
        try:
            await update_run_phase_async(
                run_id,
                "market",
                "done",
                {
                    "market_snapshot": state.get("market_snapshot", {}),
                    "event_context": state.get("event_context", {}),
                },
            )

            # Update event and market IDs in run document
            await update_run_with_event_and_market_async(run_id, state)
        except Exception as db_error:
            logger.warning(
                "Failed to update run document for market phase",
                run_id=run_id,
                error=str(db_error),
                exc_info=True,
            )
            # Continue - analysis can proceed without DB updates

        logger.debug("Phase 1 completed", run_id=run_id)

        # PHASE 2: Tavily prompt + News + News summary
        logger.debug("Phase 2: News pipeline", run_id=run_id)
        # Skip tavily_prompt_agent if disabled in configuration
        config = state.get("config", {})
        if config.get("use_tavily_prompt_agent", True):
            state = await run_tavily_prompt_agent(state)
        else:
            logger.debug("Tavily prompt agent skipped (disabled in configuration)", run_id=run_id)
        state = await run_news_agent(state)
        # Skip news_summary_agent if disabled in configuration
        if config.get("use_news_summary_agent", True):
            state = await run_news_summary_agent(state)
        else:
            logger.debug("News summary agent skipped (disabled in configuration)", run_id=run_id)

        # Update run with news context
        try:
            await update_run_phase_async(
                run_id,
                "news",
                "done",
                {
                    "news_context": state.get("news_context", {}),
                },
            )
        except Exception as db_error:
            logger.warning(
                "Failed to update run document for news phase",
                run_id=run_id,
                error=str(db_error),
                exc_info=True,
            )
            # Continue - analysis can proceed without DB updates

        logger.debug("Phase 2 completed", run_id=run_id)

        # PHASE 3: Probability + Strategy + Report
        logger.debug("Phase 3: Signal and Report", run_id=run_id)
        state = await run_prob_agent(state)
        state = await run_strategy_agent(state)
        state = await run_report_agent(state)

        # Serialize signal if it's a Pydantic model
        signal_raw = state.get("signal", {})
        if hasattr(signal_raw, "model_dump"):
            signal = signal_raw.model_dump()
        elif hasattr(signal_raw, "dict"):
            signal = signal_raw.dict()
        elif isinstance(signal_raw, dict):
            signal = signal_raw
        else:
            signal = {}

        # Update run with signal, decision, and report
        try:
            await update_run_phase_async(
                run_id,
                "signal",
                "done",
                {
                    "signal": signal,
                    "decision": state.get("decision", {}),
                },
            )

            await update_run_phase_async(
                run_id,
                "report",
                "done",
                {
                    "report": state.get("report", {}),
                },
            )
        except Exception as db_error:
            logger.warning(
                "Failed to update run document for signal/report phases",
                run_id=run_id,
                error=str(db_error),
                exc_info=True,
            )
            # Continue - analysis can proceed without DB updates

        logger.debug("Phase 3 completed", run_id=run_id)

        # Final persistence (for backward compatibility and trace support)
        try:
            await persist_run_snapshot_async(state)
            logger.info("Phased analysis completed successfully", run_id=run_id)
        except Exception as persist_error:
            # Log but don't fail - the phased updates are already done
            logger.warning(
                "Failed to persist final snapshot",
                run_id=run_id,
                error=str(persist_error),
                exc_info=True,
            )

    except Exception as e:
        logger.error(
            "Phased analysis failed",
            run_id=run_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        # Mark all remaining phases as error
        for phase in ["market", "news", "signal", "report"]:
            try:
                await update_run_phase_async(run_id, phase, "error")
            except Exception as update_error:
                logger.warning(
                    "Failed to update phase status to error",
                    run_id=run_id,
                    phase=phase,
                    error=str(update_error),
                )
        raise
