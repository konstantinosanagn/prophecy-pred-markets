"""Event agent - normalizes event metadata."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.agents.state import AgentState
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def _derive_event_slug(market_slug: str | None) -> str:
    if not market_slug:
        return "unknown-event"
    parts = market_slug.split("-")
    if len(parts) <= 1:
        return market_slug
    return "-".join(parts[:-1]) or market_slug


async def run_event_agent(state: AgentState) -> AgentState:
    """Normalize event metadata and provide denormalized context.

    This agent can run in parallel with news_agent since it only processes
    data already available in state.
    """
    market_slug = state.get("slug")
    logger.debug("Running event agent", market_slug=market_slug)
    event = state.get("event", {})
    event_slug = event.get("slug") or _derive_event_slug(market_slug)
    gamma_event_id = event.get("gamma_event_id") or f"evt-{event_slug}"
    title = event.get("title") or f"{event_slug.replace('-', ' ').title()}?"
    description = event.get(
        "description",
        "Placeholder description for the macro event associated with this market.",
    )
    category = event.get("category") or "Macro"
    # Use image from event if available (set by market_agent from Polymarket API),
    # otherwise use fallback
    image = event.get("image") or None  # Don't use fallback, let frontend handle missing images
    end_date = event.get("end_date") or (datetime.now(timezone.utc) + timedelta(days=30)).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")
    timestamp = state.get("run_at") or datetime.now(timezone.utc).isoformat()

    # Preserve commentCount, seriesCommentCount, and volume24hr from the original
    # event data (set by market_agent)
    original_comment_count = event.get("commentCount")
    original_series_comment_count = event.get("seriesCommentCount")
    original_volume24hr = event.get("volume24hr")

    state["event"] = {
        "gamma_event_id": gamma_event_id,
        "slug": event_slug,
        "title": title,
        "description": description,
        "category": category,
        "image": image,
        "end_date": end_date,
        "created_at": event.get("created_at", timestamp),
        "updated_at": timestamp,
    }
    # IMPORTANT: Preserve commentCount and volume24hr from API (set by market_agent)
    if original_comment_count is not None:
        state["event"]["commentCount"] = original_comment_count
    if original_series_comment_count is not None:
        state["event"]["seriesCommentCount"] = original_series_comment_count
    if original_volume24hr is not None:
        state["event"]["volume24hr"] = original_volume24hr

    state["event_description"] = description

    # Get additional event data from state (set by market_agent)
    event_data = state.get("event", {})
    volume24hr = event_data.get("volume24hr")
    # Get commentCount, allowing 0 values (explicitly check for None)
    commentCount = event_data.get("commentCount") if "commentCount" in event_data else None
    seriesCommentCount = (
        event_data.get("seriesCommentCount") if "seriesCommentCount" in event_data else None
    )

    # Log to verify commentCount is preserved
    logger.debug(
        "Event agent - commentCount handling",
        original_comment_count=original_comment_count,
        commentCount_in_event_context=commentCount,
        commentCount_in_state_event=state["event"].get("commentCount"),
        seriesCommentCount_in_event_context=seriesCommentCount,
        seriesCommentCount_in_state_event=state["event"].get("seriesCommentCount"),
    )
    url = state.get("polymarket_url") or state.get("market_url")

    state["event_context"] = {
        "title": title,
        "description": description,
        "category": category,
        "image": image,
        "volume24hr": volume24hr,
        "commentCount": commentCount,  # Can be None, 0, or a number
        "seriesCommentCount": seriesCommentCount,
        "url": url,
    }
    return state
