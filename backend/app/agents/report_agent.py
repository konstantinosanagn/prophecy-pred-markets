"""Report agent - generates structured AI reports with fallback."""

from __future__ import annotations

import json
from textwrap import dedent
from typing import Any, Mapping

from pydantic import BaseModel

from app.agents.state import AgentState
from app.core.logging_config import get_logger
from app.services.openai_client import get_openai_client

logger = get_logger(__name__)


def _signal_to_dict(signal: Any) -> dict:
    """Normalize Signal into a plain dict for downstream usage."""
    if isinstance(signal, BaseModel):
        return signal.model_dump()
    if isinstance(signal, Mapping):
        return dict(signal)
    # last-resort: nothing useful
    return {}


def _generate_fallback_report(
    market_snapshot: dict[str, Any],
    signal: dict[str, Any],
    decision: dict[str, Any],
    event_context: dict[str, Any],
    news_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Generate a basic templated report when OpenAI fails."""
    s = _signal_to_dict(signal)

    # Try multiple key names to be robust to older/newer Signal versions
    market_prob = (
        s.get("market_prob")
        or s.get("p_mkt")  # from prob_agent log
        or s.get("p_market")
        or s.get("model_prob_abs")
        or 0.0
    )

    model_prob = (
        s.get("model_prob")
        or s.get("p_model")  # from prob_agent log
        or s.get("model_prob_abs")
        or market_prob
    )

    edge_pct = decision.get("edge_pct") or s.get("edge_pct")
    if edge_pct is None:
        edge_pct = abs(model_prob - market_prob)

    # direction is computed but not currently used
    _direction = s.get("direction") or ("yes" if model_prob >= market_prob else "no")

    confidence = s.get("confidence_level") or s.get("confidence") or "low"

    action = decision.get("action", "HOLD")
    size = s.get("recommended_size_fraction", 0)
    tp = s.get("target_take_profit_prob")
    sl = s.get("target_stop_loss_prob")

    headline = (
        f"Model estimates {model_prob:.1%} vs market {market_prob:.1%}. "
        f"Edge {edge_pct:.2%}. Confidence {confidence.upper()}."
    )

    thesis = (
        f"Our model estimates the true probability at {model_prob:.1%}, compared to the market's "
        f"implied probability of {market_prob:.1%}, giving us an edge of {edge_pct:.2%}. "
        f"Confidence level is {confidence.upper()}. "
        f"Recommended action: {action} with position size {size:.1%}."
    )

    bull_case = [
        f"Model sees {model_prob:.1%} probability vs market {market_prob:.1%}",
        f"Edge of {edge_pct:.2%} suggests market mispricing",
    ]

    bear_case = [
        "Market may be correctly pricing the event",
        "Limited edge suggests cautious approach",
    ]

    key_risks = [
        "Model uncertainty",
        "Market volatility",
    ]

    execution_notes = f"Recommended {action} with {size:.1%} position size."
    if tp:
        execution_notes += f" Take profit at {tp:.1%}."
    if sl:
        execution_notes += f" Stop loss at {sl:.1%}."

    return {
        "headline": headline,
        "thesis": thesis,
        "bull_case": bull_case,
        "bear_case": bear_case,
        "key_risks": key_risks,
        "execution_notes": execution_notes,
        # Legacy fields for backward compatibility
        "title": headline,
        "markdown": dedent(
            f"""
            ## TL;DR
            Action: **{action}** with edge ~{edge_pct:.2%}.

            ## Market snapshot
            - Question: {market_snapshot.get("question", "N/A")}
            - Yes price: {market_snapshot.get("yes_price", 0):.2%}
            - Liquidity: {market_snapshot.get("liquidity", 0):,.0f} USDC

            ## Rationale
            {decision.get("notes", "Strategy placeholder.")}
            """
        ).strip(),
    }


async def _generate_report_with_openai(
    market_snapshot: dict[str, Any],
    signal: dict[str, Any],
    decision: dict[str, Any],
    event_context: dict[str, Any],
    news_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Generate structured report using OpenAI."""
    try:
        client = get_openai_client()
    except Exception as exc:
        logger.warning("Failed to get OpenAI client", error=str(exc))
        raise RuntimeError("OpenAI client not available") from exc

    if not client or not client.api_key:
        raise RuntimeError("OpenAI API key not configured")

    # Extract key data
    s = _signal_to_dict(signal)

    market_question = market_snapshot.get("question", "N/A")
    yes_price = market_snapshot.get("yes_price", 0)

    market_prob = (
        s.get("market_prob")
        or s.get("p_mkt")
        or s.get("p_market")
        or s.get("model_prob_abs")
        or yes_price
        or 0.0
    )

    model_prob = (
        s.get("model_prob")
        or s.get("p_model")
        or s.get("model_prob_abs")
        or market_prob
        or yes_price
        or 0.0
    )

    edge_pct = decision.get("edge_pct") or s.get("edge_pct")
    if edge_pct is None:
        edge_pct = abs(model_prob - market_prob)

    # direction is computed but not currently used
    _direction = s.get("direction") or ("yes" if model_prob >= market_prob else "no")

    confidence = s.get("confidence_level") or s.get("confidence") or "low"

    kelly = s.get("kelly_fraction_yes", 0)
    confidence_score = s.get("confidence_score", 0.5)
    action = decision.get("action", "HOLD")
    size = s.get("recommended_size_fraction", 0)
    tp = s.get("target_take_profit_prob")
    sl = s.get("target_stop_loss_prob")
    rationale = s.get("rationale_short") or s.get("rationale", "")

    # Format tp and sl safely for string formatting
    tp_str = f"{tp:.4f} ({tp * 100:.2f}%)" if tp is not None else "None (N/A)"
    sl_str = f"{sl:.4f} ({sl * 100:.2f}%)" if sl is not None else "None (N/A)"

    # News summary and sentiment
    news_summary = ""
    sentiment_dist = ""
    if news_context:
        news_summary = news_context.get("summary", news_context.get("combined_summary", ""))
        articles = news_context.get("articles", [])
        if articles:
            bullish = sum(1 for a in articles if a.get("sentiment") == "bullish")
            bearish = sum(1 for a in articles if a.get("sentiment") == "bearish")
            neutral = sum(1 for a in articles if a.get("sentiment") == "neutral")
            total = len(articles)
            if total > 0:
                sentiment_dist = (
                    f"Bullish: {bullish} ({bullish / total * 100:.0f}%), "
                    f"Bearish: {bearish} ({bearish / total * 100:.0f}%), "
                    f"Neutral: {neutral} ({neutral / total * 100:.0f}%)"
                )

    # event_title is not currently used but may be needed for future features
    _event_title = event_context.get("title", "Market")

    system_msg = (
        "You are writing a concise trade note for a prediction market. "
        "You will receive structured data about the market, model signal, "
        "news, and recommended action. "
        "Return ONLY a valid JSON object with the exact fields specified. "
        "Do not include any markdown formatting or code blocks."
    )

    user_msg = f"""
You are analyzing a prediction market trade. Here is the structured data:

**Market Snapshot:**
- Question: {market_question}
- YES price: {yes_price:.4f} ({yes_price * 100:.2f}%)
- Market implied probability: {market_prob:.4f} ({market_prob * 100:.2f}%)

**Model Signal:**
- Model probability: {model_prob:.4f} ({model_prob * 100:.2f}%)
- Edge: {edge_pct:.4f} ({edge_pct * 100:.2f} percentage points)
- Kelly fraction (YES): {kelly:.4f} ({kelly * 100:.2f}%)
- Confidence: {confidence.upper()} (score: {confidence_score:.2f})
- Rationale: {rationale or "No rationale provided"}

**Recommended Action:**
- Action: {action}
- Position size: {size:.4f} ({size * 100:.2f}%)
- Take profit: {tp_str}
- Stop loss: {sl_str}

**News Context:**
{f"Summary: {news_summary}" if news_summary else "No news summary available"}
{f"Sentiment distribution: {sentiment_dist}" if sentiment_dist else ""}

Return a JSON object with these exact fields:
{{
  "headline": "1 sentence, punchy, mention model vs market if relevant",
  "thesis": "3-5 sentences tying together market context, news, and model edge",
  "bull_case": ["bullet 1", "bullet 2", "bullet 3"],
  "bear_case": ["bullet 1", "bullet 2", "bullet 3"],
  "key_risks": ["risk 1", "risk 2", "risk 3"],
  "execution_notes": (
      "2-3 sentences on how to size, how to use TP/SL, "
      "and when to re-check the market"
  )
}}

Requirements:
- headline: 1 sentence, punchy, mention model vs market if relevant
- thesis: 3-5 sentences tying together market context, news, and model edge
- bull_case: 2-4 short bullet points (as array of strings)
- bear_case: 2-4 short bullet points (as array of strings)
- key_risks: 2-4 short bullet points (as array of strings)
- execution_notes: 2-3 sentences on sizing, TP/SL usage, and when to re-check

Return ONLY the JSON object, no other text.
"""

    try:
        # Use OpenAI client's sync method in executor
        import asyncio

        def _call_openai():
            if not client.client:
                raise RuntimeError("OpenAI client not initialized")

            if client._use_new_api:
                try:
                    # Try with response_format (newer API versions)
                    completion = client.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": user_msg},
                        ],
                        temperature=0.3,
                        response_format={"type": "json_object"},
                    )
                except (TypeError, AttributeError):
                    # Fallback if response_format not supported
                    completion = client.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": user_msg},
                        ],
                        temperature=0.3,
                    )
                return completion.choices[0].message.content
            else:
                import openai

                if not openai.api_key:
                    raise RuntimeError("OpenAI API key not configured")
                completion = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.3,
                )
                return completion.choices[0].message["content"]

        # Use get_running_loop() for better compatibility
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        raw_content = await loop.run_in_executor(None, _call_openai)

        # Parse JSON response
        # Remove markdown code blocks if present
        content = raw_content.strip()
        if content.startswith("```"):
            # Extract JSON from code block
            lines = content.split("\n")
            if lines[-1].startswith("```"):
                content = "\n".join(lines[1:-1])
            else:
                content = "\n".join(lines[1:])
        elif content.startswith("```json"):
            lines = content.split("\n")
            if lines[-1].startswith("```"):
                content = "\n".join(lines[1:-1])
            else:
                content = "\n".join(lines[1:])

        report_data = json.loads(content)

        # Validate required fields
        required_fields = [
            "headline",
            "thesis",
            "bull_case",
            "bear_case",
            "key_risks",
            "execution_notes",
        ]
        for field in required_fields:
            if field not in report_data:
                logger.warning(f"Missing field {field} in OpenAI response, using fallback")
                return _generate_fallback_report(
                    market_snapshot, signal, decision, event_context, news_context
                )

        # Ensure arrays are lists
        for field in ["bull_case", "bear_case", "key_risks"]:
            if not isinstance(report_data[field], list):
                report_data[field] = [str(report_data[field])]

        # Add legacy fields for backward compatibility
        report_data["title"] = report_data["headline"]
        report_data["markdown"] = dedent(
            f"""
            ## TL;DR
            {report_data["headline"]}

            ## Thesis
            {report_data["thesis"]}

            ## Bull Case
            {chr(10).join(f"- {point}" for point in report_data["bull_case"])}

            ## Bear Case
            {chr(10).join(f"- {point}" for point in report_data["bear_case"])}

            ## Key Risks
            {chr(10).join(f"- {risk}" for risk in report_data["key_risks"])}

            ## Execution Notes
            {report_data["execution_notes"]}
            """
        ).strip()

        return report_data

    except Exception as exc:
        logger.warning(
            "OpenAI report generation failed, using fallback",
            error=str(exc),
            exc_info=True,
        )
        return _generate_fallback_report(
            market_snapshot, signal, decision, event_context, news_context
        )


async def run_report_agent(state: AgentState) -> AgentState:
    """Generate a structured AI report with fallback to template.

    This agent must run last as it needs the decision from strategy_agent.
    """
    logger.debug("Running report agent")

    try:
        decision = state.get("decision", {})
        market_snapshot = state.get("market_snapshot", {})
        event_context = state.get("event_context", {})
        signal = state.get("signal", {})
        news_context = state.get("news_context")

        # Try to generate with OpenAI, fallback to template
        try:
            report = await _generate_report_with_openai(
                market_snapshot, signal, decision, event_context, news_context
            )
            logger.debug("Report generated successfully with OpenAI")
        except Exception as exc:
            logger.warning(
                "Report generation failed, using fallback template",
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True,
            )
            report = _generate_fallback_report(
                market_snapshot, signal, decision, event_context, news_context
            )

        state["report"] = report
        state["env"] = state.get("env") or {
            "app_version": "0.1.0",
            "model": "gpt-4o-mini",
            "tavily_version": "v1",
            "langgraph_graph_version": "market-v1",
        }

        return state
    except Exception as exc:
        # Last resort: ensure we always return a valid state with a report
        logger.error(
            "Critical error in report agent, using minimal fallback",
            error=str(exc),
            error_type=type(exc).__name__,
            exc_info=True,
        )
        # Generate minimal fallback report
        decision = state.get("decision", {})
        market_snapshot = state.get("market_snapshot", {})
        event_context = state.get("event_context", {})
        signal = state.get("signal", {})
        news_context = state.get("news_context")

        report = _generate_fallback_report(
            market_snapshot, signal, decision, event_context, news_context
        )
        state["report"] = report
        return state
