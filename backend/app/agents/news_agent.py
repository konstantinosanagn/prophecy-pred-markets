"""News agent - aggregates news using Tavily API."""

from __future__ import annotations

from typing import Any, Dict, List

from app.agents.state import AgentState
from app.agents.tavily_prompt_agent import TavilyQuerySpec
from app.core.logging_config import get_logger
from app.core.sentiment_analyzer import analyze_articles_sentiment
from app.services.tavily_client import search_news

logger = get_logger(__name__)


def _normalize_tavily_queries(raw: Any) -> List[TavilyQuerySpec]:
    """Normalize tavily_queries from state to a list of TavilyQuerySpec.

    Handles both legacy format (list of strings) and new format (list of TavilyQuerySpec dicts).
    """
    specs: List[TavilyQuerySpec] = []

    if not raw:
        return specs

    if not isinstance(raw, list):
        logger.warning("tavily_queries is not a list, ignoring", raw_type=type(raw).__name__)
        return specs

    for item in raw:
        if isinstance(item, str):
            # Legacy format: list of strings
            specs.append(
                {
                    "name": "legacy",
                    "query": item,
                    "max_results": 8,
                    "search_depth": "basic",
                }
            )
        elif isinstance(item, dict):
            # New format: TavilyQuerySpec dict
            query = item.get("query")
            if not query or not isinstance(query, str):
                logger.warning("Skipping invalid query spec (missing or invalid query)", item=item)
                continue

            spec: TavilyQuerySpec = {
                "name": item.get("name") or "news",
                "query": query,
                "max_results": int(item.get("max_results") or 8),
                "search_depth": item.get("search_depth") or "basic",
            }

            # Optional fields
            if item.get("timeframe"):
                spec["timeframe"] = item["timeframe"]
            if item.get("notes"):
                spec["notes"] = item["notes"]

            specs.append(spec)
        else:
            logger.warning("Skipping invalid query item", item_type=type(item).__name__)

    return specs


def _build_fallback_query(state: AgentState) -> str:
    """Build a single fallback query from event/market context."""
    event_ctx = state.get("event_context", {}) or {}
    market_snapshot = state.get("market_snapshot", {}) or {}
    event_data = state.get("event", {}) or {}

    event_title = (
        event_ctx.get("title")
        or event_data.get("title")
        or market_snapshot.get("question")
        or "key event"
    )
    market_question = market_snapshot.get("question")

    base = (event_title or market_question or "key event").replace("?", "")
    return f"Latest news and developments relevant to: {base}"


def _build_fallback_queries(event_title: str, market_question: str | None) -> List[str]:
    """Construct a small set of Tavily queries from event/market context (fallback)."""
    base = (event_title or market_question or "key event").replace("?", "")
    queries = [
        f"{base} latest news",
        f"{base} market expectations",
    ]

    lower = base.lower()
    if "fed" in lower or "interest rate" in lower:
        queries.append(f"{base} inflation data and FOMC guidance")
    if "election" in lower or "presidential" in lower:
        queries.append(f"{base} polling averages and latest polls")

    seen = set()
    uniq: List[str] = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq


def _summarize_news_brief(queries_block: List[Dict[str, Any]]) -> str:
    """Generate a brief summary of collected news queries.

    This is a simple heuristic summary that can be replaced later with an LLM summarizer.
    """
    total_docs = sum(len(q.get("results", [])) for q in queries_block)
    names = ", ".join(q.get("name", "unnamed") for q in queries_block)
    return f"Collected {total_docs} news articles across queries: {names}."


async def run_news_agent(state: AgentState) -> AgentState:
    """Populate `news_context` using Tavily, with graceful fallback.

    This agent now depends on tavily_prompt_agent for query generation,
    but falls back to simple queries if tavily_queries is not available.
    """
    # Check Tavily API key configuration
    from app.services.tavily_client import TAVILY_API_KEY
    
    if not TAVILY_API_KEY:
        logger.error(
            "TAVILY_API_KEY is not configured - news agent cannot fetch articles",
            run_id=state.get("run_id"),
        )
    else:
        logger.debug(
            "Tavily API key is configured",
            run_id=state.get("run_id"),
            key_length=len(TAVILY_API_KEY) if TAVILY_API_KEY else 0,
        )
    
    # Get configuration early
    config = state.get("config", {})

    event_ctx = state.get("event_context", {}) or {}
    market_snapshot = state.get("market_snapshot", {}) or {}
    event_data = state.get("event", {}) or {}

    # event_title and existing_news are not currently used but may be needed for future features
    # Keeping them for potential future use
    _event_title = (
        event_ctx.get("title")
        or event_data.get("title")
        or market_snapshot.get("question")
        or "Key event"
    )

    _existing_news = state.get("news_context") or {}

    # Normalize tavily_queries from state (handles both string and TavilyQuerySpec formats)
    raw_queries = state.get("tavily_queries")
    query_specs = _normalize_tavily_queries(raw_queries)

    # Track if we're using LLM-generated queries (vs fallback)
    # If raw_queries exists and has items, and first item is a dict, it's from LLM
    using_llm_queries = (
        raw_queries
        and isinstance(raw_queries, list)
        and len(raw_queries) > 0
        and isinstance(raw_queries[0], dict)
        and "query" in raw_queries[0]
    )

    # If no queries after normalization, use fallback
    if not query_specs:
        fallback_query = _build_fallback_query(state)
        # Use configured max_articles_per_query for fallback
        fallback_max_results = config.get("max_articles_per_query", 8)
        query_specs = [
            {
                "name": "fallback",
                "query": fallback_query,
                "max_results": fallback_max_results,
                "search_depth": "basic",
            }
        ]
        using_llm_queries = False
        logger.debug(
            "Using fallback query (tavily_queries not available or empty)",
            query=fallback_query,
        )
    else:
        logger.debug(
            "Using normalized Tavily queries",
            query_count=len(query_specs),
            query_names=[q.get("name", "unnamed") for q in query_specs],
            using_llm_queries=using_llm_queries,
        )

    # Execute queries and collect results
    all_articles: List[Dict[str, Any]] = []
    answers: list[str] = []
    query_results: List[Dict[str, Any]] = []

    # Get configuration for max_articles_per_query (already retrieved above)
    default_max_per_query = config.get("max_articles_per_query", 8)

    # Search queries sequentially (they're already cached, so this is fast)
    for spec in query_specs:
        query = spec["query"]
        # Use configured max_articles_per_query if not specified in spec
        max_results = spec.get("max_results") or default_max_per_query
        # Clamp to valid range
        max_results = max(5, min(12, max_results))
        search_depth = spec.get("search_depth", "basic")

        # Note: Tavily API may not support search_depth parameter yet
        # We'll log a debug message if it's set to "advanced" but can't be used
        if search_depth == "advanced":
            logger.debug(
                "search_depth=advanced requested, but Tavily API may not support it yet",
                query=query,
            )

        try:
            result = await search_news(query, max_results=max_results, search_depth=search_depth)
            answer = result.get("answer")
            if isinstance(answer, str) and answer.strip():
                answers.append(answer)

            articles = result.get("articles") or []
            if not articles:
                logger.warning(
                    "Tavily search returned no articles",
                    query=query,
                    max_results=max_results,
                    has_answer=bool(answer),
                )
            else:
                logger.debug(
                    "Tavily search successful",
                    query=query,
                    articles_count=len(articles),
                )
            all_articles.extend(articles)
        except Exception as e:
            logger.error(
                "Failed to search Tavily for query",
                query=query,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            # Continue with other queries even if one fails
            continue

        # Store structured result
        query_results.append(
            {
                "name": spec.get("name", "unnamed"),
                "query": query,
                "results": articles,
                "answer": answer if isinstance(answer, str) else "",
            }
        )

    # Deduplicate articles by URL
    deduped: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()
    for art in all_articles:
        url = art.get("url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(art)

    # Analyze sentiment for articles based on market context (if enabled)
    market_question = market_snapshot.get("question") or ""
    yes_price = float(market_snapshot.get("yes_price", 0.5))
    outcomes = market_snapshot.get("outcomes") or ["Yes", "No"]

    # Get signal direction if available (from previous run or current state)
    signal_direction = state.get("signal", {}).get("direction")

    # Analyze sentiment for each article (if enabled in configuration)
    enable_sentiment = config.get("enable_sentiment_analysis", True)
    if enable_sentiment:
        deduped_with_sentiment = analyze_articles_sentiment(
            articles=deduped,
            market_question=market_question,
            yes_price=yes_price,
            signal_direction=signal_direction,
            outcomes=outcomes,
        )
    else:
        # Skip sentiment analysis, just use articles as-is
        deduped_with_sentiment = deduped
        logger.debug("Sentiment analysis skipped (disabled in configuration)")

    logger.debug(
        "Sentiment analysis completed",
        total_articles=len(deduped_with_sentiment),
        bullish_count=sum(1 for a in deduped_with_sentiment if a.get("sentiment") == "bullish"),
        bearish_count=sum(1 for a in deduped_with_sentiment if a.get("sentiment") == "bearish"),
        neutral_count=sum(1 for a in deduped_with_sentiment if a.get("sentiment") == "neutral"),
    )

    # Build news_context with backward compatibility
    # Keep tavily_queries as list of strings for backward compat
    query_strings = [spec["query"] for spec in query_specs]

    # Limit articles based on configuration
    # Get max_articles from config, default to 15
    max_articles_config = config.get("max_articles", 15)
    articles_for_context = deduped_with_sentiment[:max_articles_config]

    # Generate combined summary
    combined_summary = _summarize_news_brief(query_results)
    
    # If no articles found, provide a helpful message
    if not articles_for_context:
        logger.warning(
            "News agent completed with no articles",
            query_count=len(query_specs),
            queries=query_strings,
            using_llm_queries=using_llm_queries,
        )
        # Ensure we have at least a basic summary even if no articles
        if not combined_summary or combined_summary.strip() == "":
            event_title = (
                event_ctx.get("title")
                or event_data.get("title")
                or market_snapshot.get("question")
                or "this event"
            )
            combined_summary = (
                f"No recent news articles found for {event_title}. "
                "This may indicate limited coverage or the event is too recent."
            )

    # Note: Summary generation is now handled by news_summary_agent
    # We set a placeholder here; news_summary_agent will populate it
    state["news_context"] = {
        "tavily_queries": query_strings,  # Backward compatibility: list of query strings
        "queries": query_results,  # New: structured query results with metadata
        # Brief summary of collected queries
        "combined_summary": combined_summary,
        "articles": articles_for_context,  # Articles with sentiment analysis (up to 15)
        # Summary will be populated by news_summary_agent
    }

    logger.info(
        "News agent completed",
        run_id=state.get("run_id"),
        query_count=len(query_specs),
        articles_found=len(deduped_with_sentiment),
        articles_in_context=len(articles_for_context),
        using_llm_queries=using_llm_queries,
        has_summary=bool(combined_summary),
        news_context_keys=list(state.get("news_context", {}).keys()),
    )
    
    # Log detailed article info for debugging
    if articles_for_context:
        logger.debug(
            "News articles collected",
            run_id=state.get("run_id"),
            article_titles=[a.get("title", "N/A")[:50] for a in articles_for_context[:3]],
            total_articles=len(articles_for_context),
        )
    else:
        logger.warning(
            "News agent completed with NO articles",
            run_id=state.get("run_id"),
            query_count=len(query_specs),
            queries=[q.get("query", "N/A")[:50] for q in query_specs],
            all_articles_count=len(all_articles),
            deduped_count=len(deduped_with_sentiment),
        )

    return state
