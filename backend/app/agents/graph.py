"""Multi-agent analysis graph orchestration with parallel execution."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

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

logger = get_logger(__name__)


async def run_analysis_graph(initial_state: AgentState) -> AgentState:
    """Run the multi-agent analysis graph with parallel execution where possible.

    Execution flow:
    1. market_agent (sequential - must run first)
    2. event_agent (sequential - depends on market_agent)
    3. tavily_prompt_agent (sequential - depends on event_agent)
    4. news_agent (sequential - depends on tavily_prompt_agent)
    5. news_summary_agent (sequential - depends on news_agent)
    6. prob_agent (sequential - depends on news_summary_agent)
    7. strategy_agent (sequential - depends on prob_agent)
    8. report_agent (sequential - depends on strategy_agent)
    """
    run_id = f"run-{uuid4().hex}"
    state: AgentState = dict(initial_state)
    state.setdefault("run_id", run_id)
    state.setdefault(
        "run_at",
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )
    state.setdefault("market_url", state.get("polymarket_url", "https://polymarket.com"))

    logger.info("Starting analysis graph", run_id=run_id, market_url=state.get("market_url"))

    # Step 1: Market agent must run first
    state = await run_market_agent(state)
    logger.debug("Market agent completed", run_id=run_id)

    # Step 2: Event agent (depends on market_agent)
    state = await run_event_agent(state)
    logger.debug("Event agent completed", run_id=run_id)

    # Step 3: Tavily prompt agent (depends on event_agent for event_context)
    # Skip if disabled in configuration
    config = state.get("config", {})
    if config.get("use_tavily_prompt_agent", True):
        state = await run_tavily_prompt_agent(state)
        logger.debug("Tavily prompt agent completed", run_id=run_id)
    else:
        logger.debug("Tavily prompt agent skipped (disabled in configuration)", run_id=run_id)
        # Don't set tavily_queries - news_agent will use fallback

    # Step 4: News agent (depends on tavily_prompt_agent for tavily_queries)
    state = await run_news_agent(state)
    logger.debug("News agent completed", run_id=run_id)

    # Step 5: News summary agent (depends on news_agent for articles with sentiment)
    # Skip if disabled in configuration
    if config.get("use_news_summary_agent", True):
        state = await run_news_summary_agent(state)
        logger.debug("News summary agent completed", run_id=run_id)
    else:
        logger.debug("News summary agent skipped (disabled in configuration)", run_id=run_id)

    # Step 6: Probability agent (depends on news_context with summary)
    state = await run_prob_agent(state)
    logger.debug("Probability agent completed", run_id=run_id)

    # Step 7: Strategy agent (depends on signal)
    state = await run_strategy_agent(state)
    logger.debug("Strategy agent completed", run_id=run_id)

    # Step 8: Report agent (depends on decision)
    state = await run_report_agent(state)
    logger.debug("Report agent completed", run_id=run_id)

    logger.info("Analysis graph completed", run_id=run_id)
    return state
