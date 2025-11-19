"""Tavily prompt agent - generates structured Tavily query specifications using LLM."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Literal, Optional, TypedDict

from app.agents.state import AgentState
from app.core.logging_config import get_logger
from app.services.openai_client import get_openai_client

logger = get_logger(__name__)

try:
    import openai
except ImportError:  # pragma: no cover - handled at runtime
    openai = None  # type: ignore[assignment]


class TavilyQuerySpec(TypedDict, total=False):
    """Structured specification for a single Tavily query."""

    name: str
    query: str
    max_results: int
    search_depth: Literal["basic", "advanced"]
    timeframe: Optional[str]  # e.g. "24h", "7d", "30d"
    notes: Optional[str]


SYSTEM_PROMPT = """You are a research director for a prediction-market analysis system.

Your job: turn a Polymarket market description into 1–3 structured web search
queries for Tavily that help determine the TRUE probability of the YES outcome.

Constraints:
- Focus ONLY on information that affects whether the market resolves YES or NO.
- Disambiguate ambiguous entities (e.g., "Biden" → "Joe Biden, President of the United States").
- Tune queries to the given analysis horizon:
  * "intraday": emphasize latest developments, breaking news, live events.
  * "24h": mix of latest updates + near-term catalysts.
  * "resolution": structural factors, long-term drivers, track record, polls, fundamentals.

Return ONLY a JSON object with a "queries" field containing a list of 1–3 query objects.
Each query object must have:
- "name" (short slug, e.g. "latest_developments")
- "query" (full natural-language query string)
- "max_results" (integer between 5 and 12)
- "search_depth" ("basic" or "advanced")
- "timeframe" (optional; "24h" / "7d" / "30d" or empty string)

Only output valid JSON. No extra text or prose."""


def build_prompt_from_state(state: AgentState) -> str:
    """Render a compact text prompt for the LLM based on current agent state."""
    market = state.get("market_snapshot", {}) or {}
    event = state.get("event_context", {}) or {}
    event_doc = state.get("event", {}) or {}

    question = market.get("question") or ""
    outcomes = market.get("outcomes") or []
    category = event.get("category") or event_doc.get("category") or ""
    region = event.get("region") or ""
    resolution_criteria = event.get("resolution_criteria") or ""

    horizon = state.get("horizon") or "24h"
    strategy_preset = state.get("strategy_preset") or "Balanced"

    return f"""Market snapshot:
- Question: {question}
- Outcomes: {outcomes}
- Category: {category}
- Region: {region}
- Resolution criteria: {resolution_criteria}

Analysis horizon: {horizon}
Strategy preset: {strategy_preset}

Generate 1–3 Tavily query specifications optimized for this market and horizon.""".strip()


def parse_tavily_specs(raw_json: dict) -> List[TavilyQuerySpec]:
    """Convert raw LLM JSON into a list of TavilyQuerySpec, with light validation."""
    queries: List[TavilyQuerySpec] = []

    raw_queries = raw_json.get("queries", [])
    if not isinstance(raw_queries, list):
        logger.warning(
            "LLM response 'queries' field is not a list",
            raw_type=type(raw_queries).__name__,
        )
        return queries

    for item in raw_queries:
        if not isinstance(item, dict):
            logger.warning("Skipping invalid query item", item_type=type(item).__name__)
            continue

        name = item.get("name") or "news"
        query = item.get("query") or ""
        if not query:
            logger.warning("Skipping query with empty query string", name=name)
            continue

        # Validate max_results
        max_results_raw = item.get("max_results")
        try:
            max_results = int(max_results_raw) if max_results_raw is not None else 8
            max_results = max(5, min(12, max_results))  # Clamp between 5 and 12
        except (ValueError, TypeError):
            logger.warning("Invalid max_results, using default", max_results_raw=max_results_raw)
            max_results = 8

        # Validate search_depth
        search_depth_raw = item.get("search_depth", "basic")
        if search_depth_raw not in ("basic", "advanced"):
            logger.warning("Invalid search_depth, using 'basic'", search_depth=search_depth_raw)
            search_depth = "basic"
        else:
            search_depth = search_depth_raw  # type: ignore[assignment]

        spec: TavilyQuerySpec = {
            "name": name,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
        }

        # Optional fields
        timeframe = item.get("timeframe")
        if timeframe and isinstance(timeframe, str):
            spec["timeframe"] = timeframe

        notes = item.get("notes")
        if notes and isinstance(notes, str):
            spec["notes"] = notes

        queries.append(spec)

    return queries


def _generate_tavily_queries_sync(
    system_prompt: str,
    user_prompt: str,
    cache_key: str,
) -> Dict[str, Any]:
    """Generate Tavily query specifications using OpenAI (sync method)."""
    if openai is None:
        logger.warning("OpenAI not available")
        raise RuntimeError("OpenAI is not available")

    openai_client = get_openai_client()
    if not openai_client.api_key:
        logger.warning("OPENAI_API_KEY not configured")
        raise RuntimeError("OpenAI API key not configured")

    # Try cache first
    from app.core.cache import openai_cache

    cached_result = openai_cache.get(cache_key)
    if cached_result is not None:
        logger.debug("Cache hit for Tavily query generation")
        return cached_result

    # Check circuit breaker
    from app.core.resilience import openai_circuit

    if not openai_circuit.can_attempt():
        logger.warning("OpenAI circuit breaker is OPEN")
        raise RuntimeError("OpenAI circuit breaker is OPEN")

    # Cache miss - call OpenAI
    raw_content = None
    try:
        logger.debug("Cache miss - calling OpenAI API for Tavily queries")
        # Use OpenAI client from openai_client.py which handles both old and new API formats
        if openai_client.client and openai_client._use_new_api:
            # New API format (v1.0+)
            completion = openai_client.client.chat.completions.create(
                model="gpt-4o-mini",  # gpt-5-mini doesn't exist yet, using gpt-4o-mini
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            raw_content = completion.choices[0].message.content
        else:
            # Old API format (v0.x) - fallback
            completion = openai.ChatCompletion.create(
                model="gpt-4o-mini",  # gpt-5-mini doesn't exist yet, using gpt-4o-mini
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            raw_content = completion.choices[0].message["content"]

        if not raw_content:
            raise ValueError("OpenAI returned empty response")

        # Clean up the response - remove markdown code blocks if present
        content_cleaned = raw_content.strip()
        if content_cleaned.startswith("```json"):
            # Remove ```json and closing ```
            content_cleaned = content_cleaned[7:]  # Remove "```json"
            if content_cleaned.endswith("```"):
                content_cleaned = content_cleaned[:-3]
            content_cleaned = content_cleaned.strip()
        elif content_cleaned.startswith("```"):
            # Remove generic code blocks
            content_cleaned = content_cleaned[3:]
            if content_cleaned.endswith("```"):
                content_cleaned = content_cleaned[:-3]
            content_cleaned = content_cleaned.strip()

        data = json.loads(content_cleaned)
        openai_circuit.record_success()

        # Cache successful result
        openai_cache.set(cache_key, data)
        logger.debug("OpenAI API call successful and cached")
        return data
    except json.JSONDecodeError as exc:
        openai_circuit.record_failure()
        content_preview = raw_content[:200] if raw_content else "<no content>"
        logger.warning(
            "Failed to parse OpenAI JSON response",
            error=str(exc),
            raw_content=content_preview,
        )
        raise ValueError(f"Invalid JSON from OpenAI: {exc}") from exc
    except Exception as exc:
        openai_circuit.record_failure()
        logger.warning("OpenAI call failed", error=str(exc), exc_info=True)
        raise


async def run_tavily_prompt_agent(state: AgentState) -> AgentState:
    """Generate structured Tavily query specifications using an LLM.

    Inputs (from AgentState):
      - market_snapshot
      - event_context
      - horizon
      - strategy_preset
      - slug

    Outputs (into AgentState):
      - tavily_queries: List[TavilyQuerySpec] (only set on success)
    """
    # If queries are already present (e.g. cache or manual override), skip.
    if state.get("tavily_queries"):
        logger.debug("tavily_queries already present, skipping generation")
        return state

    # Extract context for logging and cache key
    market_slug = state.get("slug") or "unknown"
    horizon = state.get("horizon") or "24h"
    strategy_preset = state.get("strategy_preset") or "Balanced"
    event_slug = state.get("event", {}).get("slug") or ""

    # Build LLM prompt
    user_prompt = build_prompt_from_state(state)

    # Create cache key including horizon, slug, and strategy_preset
    # This ensures different horizons/strategies don't share cached prompts
    import hashlib

    cache_input = (
        f"{SYSTEM_PROMPT}:{user_prompt}:{horizon}:{market_slug}:{event_slug}:{strategy_preset}"
    )
    cache_key = f"openai:tavily_queries:{hashlib.md5(cache_input.encode()).hexdigest()}"

    # Call OpenAI client (sync method wrapped in async executor)
    try:
        loop = asyncio.get_event_loop()
        raw_response = await loop.run_in_executor(
            None,
            _generate_tavily_queries_sync,
            SYSTEM_PROMPT,
            user_prompt,
            cache_key,
        )

        # Parse and validate
        tavily_queries = parse_tavily_specs(raw_response)

        if not tavily_queries:
            logger.warning(
                "LLM generated no valid queries, News Agent will use fallback",
                market_slug=market_slug,
                horizon=horizon,
            )
            # Don't set tavily_queries - let news_agent handle fallback
            return state

        # Log with context
        first_query = tavily_queries[0]["query"][:180] if tavily_queries else None
        logger.info(
            "tavily_queries_generated",
            market_slug=market_slug,
            horizon=horizon,
            num_queries=len(tavily_queries),
            first_query=first_query,
            query_names=[q["name"] for q in tavily_queries],
        )

        # Only set tavily_queries on success
        state["tavily_queries"] = tavily_queries
        return state

    except RuntimeError as exc:
        # OpenAI not available or circuit breaker open
        logger.warning(
            "tavily_prompt_agent_failed",
            error=str(exc),
            market_slug=market_slug,
            horizon=horizon,
            error_type="RuntimeError",
        )
        # Don't set tavily_queries - let news_agent handle fallback
        return state
    except (ValueError, KeyError) as exc:
        # JSON parsing failed or invalid structure
        logger.warning(
            "tavily_prompt_agent_failed",
            error=str(exc),
            market_slug=market_slug,
            horizon=horizon,
            error_type=type(exc).__name__,
        )
        # Don't set tavily_queries - let news_agent handle fallback
        return state
    except Exception as exc:
        # Any other error
        logger.warning(
            "tavily_prompt_agent_failed",
            error=str(exc),
            market_slug=market_slug,
            horizon=horizon,
            error_type=type(exc).__name__,
            exc_info=True,
        )
        # Don't set tavily_queries - let news_agent handle fallback
        return state
