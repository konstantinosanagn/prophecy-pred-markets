"""News summary agent - generates comprehensive summaries using OpenAI with sentiment weighting."""

from __future__ import annotations

from typing import Any, Dict, List

from app.agents.state import AgentState
from app.core.logging_config import get_logger
from app.services.openai_client import get_openai_client

logger = get_logger(__name__)


def _generate_fallback_summary(
    event_title: str,
    answers: List[str],
    deduped_with_sentiment: List[Dict[str, Any]],
) -> str:
    """Generate a fallback summary when OpenAI is unavailable."""
    if answers:
        return "\n\n".join(f"- {a}" for a in answers if a.strip())
    elif deduped_with_sentiment:
        title_list = "; ".join(
            a.get("title", "") for a in deduped_with_sentiment[:3] if a.get("title")
        )
        return f"Recent coverage on {event_title} highlights: {title_list}."
    else:
        return (
            f"Recent coverage on {event_title} highlights cautious sentiment with "
            "participants awaiting new data releases."
        )


async def run_news_summary_agent(state: AgentState) -> AgentState:
    """Generate comprehensive news summary using OpenAI with sentiment weighting.

    This agent depends on news_agent having already:
    - Collected articles via Tavily
    - Performed sentiment analysis on articles

    The summary is weighted towards the sentiment category with the most articles,
    but includes perspectives from all sentiment categories (bullish, bearish, neutral).
    """
    event_ctx = state.get("event_context", {}) or {}
    market_snapshot = state.get("market_snapshot", {}) or {}
    event_data = state.get("event", {}) or {}
    news_context = state.get("news_context") or {}
    existing_news = news_context

    event_title = (
        event_ctx.get("title")
        or event_data.get("title")
        or market_snapshot.get("question")
        or "Key event"
    )
    market_question = market_snapshot.get("question") or ""

    # Get articles with sentiment from news_context
    articles = news_context.get("articles", [])

    # Get Tavily answers for fallback (if available)
    query_results = news_context.get("queries", [])
    answers: List[str] = []
    for query_result in query_results:
        answer = query_result.get("answer")
        if isinstance(answer, str) and answer.strip():
            answers.append(answer)

    # Generate summary using OpenAI with sentiment weighting
    summary = ""
    if existing_news.get("summary"):
        # Use existing summary if available (e.g., from cache or previous run)
        summary = existing_news["summary"]
        logger.debug("Using existing summary from news context")
    elif articles and len(articles) > 0:
        # Use OpenAI to generate comprehensive summary with sentiment weighting
        # Require at least 2 articles for meaningful sentiment-weighted summary
        if len(articles) >= 2:
            try:
                openai_client = get_openai_client()
                logger.debug(
                    "Attempting OpenAI summary generation",
                    article_count=len(articles),
                    event_title=event_title,
                )
                summary = await openai_client.summarize_news_with_sentiment(
                    articles=articles,
                    event_title=event_title,
                    market_question=market_question,
                )
                logger.info(
                    "OpenAI news summary generated successfully",
                    article_count=len(articles),
                    summary_length=len(summary),
                    summary_preview=summary[:100] if summary else "empty",
                )
            except RuntimeError as e:
                # OpenAI not available or circuit breaker open - fall back to heuristic
                logger.warning(
                    "OpenAI not available for summary, using fallback heuristic",
                    error=str(e),
                )
                summary = _generate_fallback_summary(event_title, answers, articles)
            except Exception as exc:
                # Any other error - fall back to heuristic
                logger.warning(
                    "OpenAI summary generation failed, using fallback heuristic",
                    error=str(exc),
                    error_type=type(exc).__name__,
                    exc_info=True,
                )
                summary = _generate_fallback_summary(event_title, answers, articles)
        else:
            # Too few articles for sentiment-weighted summary, use simple fallback
            logger.debug(
                "Too few articles for OpenAI summary, using fallback",
                article_count=len(articles),
            )
            summary = _generate_fallback_summary(event_title, answers, articles)
    else:
        # No articles available - use generic fallback
        logger.debug("No articles available for summary generation")
        summary = (
            f"Recent coverage on {event_title} highlights cautious sentiment with "
            "participants awaiting new data releases."
        )

    # Update news_context with the generated summary
    if "news_context" not in state:
        state["news_context"] = {}

    state["news_context"]["summary"] = summary

    logger.info(
        "News summary agent completed",
        summary_length=len(summary),
        article_count=len(articles) if articles else 0,
    )

    return state
