"""Market agent - extracts and normalizes market data."""

from __future__ import annotations

from datetime import datetime, timezone

from app.agents.state import AgentState
from app.core.logging_config import get_logger
from app.core.market_selector import find_market_by_slug, select_market_from_options
from app.core.market_transformer import build_market_options, build_market_snapshot
from app.core.polymarket_utils import extract_slug_from_url, get_event_and_markets_by_slug

logger = get_logger(__name__)


async def run_market_agent(state: AgentState) -> AgentState:
    """Fill the canonical market definition and snapshot.

    This agent must run first as it sets up market_snapshot which other agents depend on.
    """
    market_url = state.get("market_url")
    logger.debug("Running market agent", market_url=market_url)
    slug = state.get("slug") or extract_slug_from_url(market_url) or "unknown-market"

    # Fetch real data from Polymarket API (with caching, retry, circuit breaker)
    event, markets = await get_event_and_markets_by_slug(slug)

    # Detect if this is an event (has multiple markets) vs single market
    is_event = bool(markets and len(markets) > 1)
    selected_market_slug = state.get("selected_market_slug")

    # Build market options if this is an event
    if is_event:
        market_options = build_market_options(markets)
        state["market_options"] = market_options

        # Use selector to determine if we need user selection
        chosen_market, chosen_slug, requires_selection = select_market_from_options(
            markets, selected_market_slug, slug
        )

        if requires_selection:
            # Request user selection
            state["requires_market_selection"] = True
            # Populate basic event context for UI
            state["event"] = state.get("event", {})
            if event:
                if "title" in event:
                    state["event"]["title"] = event["title"]
                if "image" in event or "icon" in event:
                    state["event"]["image"] = event.get("image") or event.get("icon")
                if "volume24hr" in event:
                    state["event"]["volume24hr"] = event.get("volume24hr")
                if "commentCount" in event:
                    state["event"]["commentCount"] = event.get("commentCount")
            return state

        # When selection is not required, explicitly clear requires_market_selection
        # Remove it from state if it exists, or set it to False
        if "requires_market_selection" in state:
            del state["requires_market_selection"]
        state["requires_market_selection"] = False

        # Update selected market slug if auto-selected
        if chosen_slug and not selected_market_slug:
            selected_market_slug = chosen_slug
            state["selected_market_slug"] = chosen_slug
    else:
        # Not an event, ensure requires_market_selection is not set
        if "requires_market_selection" in state:
            del state["requires_market_selection"]

    # Find the selected market record
    selected_market_rec = None
    if selected_market_slug and markets:
        selected_market_rec = find_market_by_slug(markets, selected_market_slug)
    elif markets and len(markets) == 1:
        # Single market, use it
        selected_market_rec = markets[0]
        selected_market_slug = selected_market_rec.get("slug") or str(
            selected_market_rec.get("id", "")
        )
        state["selected_market_slug"] = selected_market_slug

    # Extract image from API response (event level or market level)
    event_image = None
    if event or markets:
        event_image = (
            (selected_market_rec.get("image") or selected_market_rec.get("icon"))
            if selected_market_rec
            else (event.get("image") or event.get("icon") if event else None)
        )
        if not event_image and is_event and not selected_market_rec and markets:
            # fallback to first market image
            first_market = markets[0]
            event_image = first_market.get("image") or first_market.get("icon")

    # Store event data in state for event_agent to use
    state["event"] = state.get("event", {})
    if event_image:
        state["event"]["image"] = event_image
        logger.debug("Fetched image from Polymarket", image_url=event_image)

    # Store event metadata from API if available
    if event:
        if "title" in event:
            state["event"]["title"] = event["title"]
        if "volume24hr" in event:
            state["event"]["volume24hr"] = event["volume24hr"]
        # IMPORTANT: Always set commentCount if present in event, even if it's 0
        if "commentCount" in event:
            comment_count_value = event["commentCount"]
            state["event"]["commentCount"] = comment_count_value
            logger.debug(
                "Set commentCount in state from event",
                commentCount=comment_count_value,
                commentCount_type=type(comment_count_value).__name__,
            )
        if "seriesCommentCount" in event:
            series_comment_value = event["seriesCommentCount"]
            state["event"]["seriesCommentCount"] = series_comment_value
            logger.debug(
                "Set seriesCommentCount in state from event",
                seriesCommentCount=series_comment_value,
                seriesCommentCount_type=type(series_comment_value).__name__,
            )

    # If event doesn't have commentCount but selected market does, use market's commentCount
    # Check explicitly to allow 0 values
    if selected_market_rec and "commentCount" not in state.get("event", {}):
        market_comment_count = None
        if (
            "commentCount" in selected_market_rec
            and selected_market_rec["commentCount"] is not None
        ):
            market_comment_count = selected_market_rec["commentCount"]
        elif (
            "comment_count" in selected_market_rec
            and selected_market_rec["comment_count"] is not None
        ):
            market_comment_count = selected_market_rec["comment_count"]

        if market_comment_count is not None:
            state["event"]["commentCount"] = market_comment_count

    # Build market data
    gamma_market_id = state.get("gamma_market_id") or f"gamma-{slug}"
    polymarket_url = state.get("polymarket_url") or market_url or "https://polymarket.com"
    timestamp = state.get("run_at") or datetime.now(timezone.utc).isoformat()

    # Get question from API or fallback
    api_question = None
    if selected_market_rec:
        api_question = selected_market_rec.get("question") or selected_market_rec.get("title")
    elif markets and len(markets) > 0:
        api_question = markets[0].get("question") or markets[0].get("title")

    question = (
        state.get("market", {}).get("question")
        or api_question
        or f"Will {slug.replace('-', ' ')} resolve to Yes?"
    )
    outcomes = state.get("market", {}).get("outcomes") or ["Yes", "No"]
    yes_index = state.get("market", {}).get("yes_index", 0)
    group_item_title = (
        selected_market_rec.get("groupItemTitle")
        if selected_market_rec
        else state.get("market", {}).get("group_item_title", "Placeholder contract")
    )

    state["market"] = {
        "gamma_market_id": gamma_market_id,
        "slug": slug,
        "polymarket_url": polymarket_url,
        "question": question,
        "outcomes": outcomes,
        "yes_index": yes_index,
        "group_item_title": group_item_title,
        "created_at": state.get("market", {}).get("created_at", timestamp),
        "updated_at": timestamp,
    }

    # Fetch order book if we have a token ID
    order_book = {}
    if selected_market_rec:
        token_id = selected_market_rec.get("token_id") or selected_market_rec.get("tokenId")
        if token_id:
            try:
                from app.services.polymarket_client import get_polymarket_client

                client = get_polymarket_client()
                order_book = await client.fetch_order_book(token_id)
                logger.debug(
                    "Fetched order book",
                    token_id=token_id,
                    has_bids=bool(order_book.get("bids")),
                )
            except Exception as e:
                logger.warning("Failed to fetch order book", token_id=token_id, error=str(e))
                order_book = {}

    # Build market snapshot using transformer with actual API market record
    market_snapshot = build_market_snapshot(
        {
            "question": question,
            "outcomes": outcomes,
            "yes_index": yes_index,
        },
        polymarket_url,
        order_book,
        state,
        slug,
        api_market_record=selected_market_rec,  # Pass actual API data
    )
    state["market_snapshot"] = market_snapshot

    state["polymarket_url"] = polymarket_url
    state["slug"] = slug

    return state
