"""Sentiment analysis for news articles based on market context."""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from app.core.logging_config import get_logger

logger = get_logger(__name__)

Sentiment = Literal["bullish", "bearish", "neutral"]


def analyze_article_sentiment(
    article: Dict[str, Any],
    market_question: str,
    yes_price: float,
    signal_direction: Optional[str] = None,
    outcomes: Optional[list[str]] = None,
) -> Sentiment:
    """Analyze sentiment of a news article relative to market position.

    This function evaluates whether an article is bullish (supports YES outcome),
    bearish (supports NO outcome), or neutral based on:
    - Article title and content
    - Market question and outcomes
    - Current YES price
    - Signal direction (if available)

    Args:
        article: Article dict with title, snippet/content
        market_question: The market question (e.g., "Will X happen?")
        yes_price: Current YES price (0-1)
        signal_direction: Optional signal direction ("up", "down", "flat")
        outcomes: Optional list of outcomes (e.g., ["Yes", "No"])

    Returns:
        "bullish", "bearish", or "neutral"
    """
    title = (article.get("title") or "").lower()
    content = (article.get("snippet") or article.get("content") or "").lower()
    text = f"{title} {content}"

    if not text.strip():
        logger.debug(
            "Article has no text for sentiment analysis",
            title=article.get("title", "")[:50],
        )
        return "neutral"

    # Extract key terms from market question
    question_lower = market_question.lower()

    # Determine what "YES" means in this market
    # Common patterns:
    # - "Will X happen?" -> YES = X happens
    # - "Will X increase?" -> YES = increase
    # - "Will X decrease?" -> YES = decrease

    # Bullish keywords (support YES outcome)
    bullish_patterns = [
        # Price/movement up
        "increase",
        "increased",
        "increasing",
        "rise",
        "rises",
        "rising",
        "rose",
        "up",
        "higher",
        "high",
        "grow",
        "growing",
        "grew",
        "gain",
        "gained",
        "gains",
        "surge",
        "surged",
        "surges",
        "rally",
        "rallied",
        "rallies",
        "soar",
        "soared",
        "jump",
        "jumped",
        "jumps",
        "climb",
        "climbed",
        "climbs",
        "boost",
        "boosted",
        # Positive sentiment
        "positive",
        "optimistic",
        "optimism",
        "strong",
        "strength",
        "stronger",
        "beat",
        "beats",
        "beaten",
        "exceed",
        "exceeded",
        "exceeds",
        "outperform",
        "outperformed",
        "outperforms",
        "success",
        "successful",
        "succeed",
        "succeeded",
        # Approval/support
        "approve",
        "approved",
        "approval",
        "pass",
        "passed",
        "passes",
        "support",
        "supported",
        "supports",
        "favor",
        "favored",
        "favors",
        "win",
        "won",
        "wins",
        "victory",
        "victories",
        "triumph",
        "triumphs",
        # Monetary policy (dovish = bullish for rate cut markets)
        "cut rates",
        "rate cut",
        "rate cuts",
        "lower rates",
        "dovish",
        "stimulus",
        "easing",
        "ease",
        "eased",
        "quantitative easing",
        "qe",
        "accommodative",
        # Market positive
        "bullish",
        "bull market",
        "rally",
        "breakthrough",
        "milestone",
        "record high",
    ]

    # Bearish keywords (support NO outcome)
    bearish_patterns = [
        # Price/movement down
        "decrease",
        "decreased",
        "decreasing",
        "fall",
        "falls",
        "fell",
        "fallen",
        "down",
        "lower",
        "low",
        "decline",
        "declined",
        "declines",
        "drop",
        "dropped",
        "drops",
        "plunge",
        "plunged",
        "plunges",
        "crash",
        "crashed",
        "crashes",
        "collapse",
        "collapsed",
        "collapses",
        "sink",
        "sank",
        "sinks",
        "slump",
        "slumped",
        "slumps",
        "dip",
        "dipped",
        "dips",
        "slide",
        "slid",
        "slides",
        # Negative sentiment
        "negative",
        "negatively",
        "pessimistic",
        "pessimism",
        "weak",
        "weaker",
        "weakness",
        "miss",
        "missed",
        "misses",
        "underperform",
        "underperformed",
        "underperforms",
        "disappoint",
        "disappointed",
        "disappoints",
        "disappointment",
        "concern",
        "concerns",
        "concerned",
        "worry",
        "worries",
        "worried",
        # Rejection/failure
        "reject",
        "rejected",
        "rejects",
        "rejection",
        "fail",
        "failed",
        "fails",
        "failure",
        "oppose",
        "opposed",
        "opposes",
        "opposition",
        "against",
        "loss",
        "losses",
        "lost",
        "defeat",
        "defeated",
        "defeats",
        # Monetary policy (hawkish = bearish for rate cut markets)
        "raise rates",
        "rate hike",
        "rate hikes",
        "hike rates",
        "hawkish",
        "tighten",
        "tightened",
        "tightening",
        "restrictive",
        "restriction",
        "restrictions",
        # Market negative
        "bearish",
        "bear market",
        "correction",
        "corrections",
        "volatility",
        "uncertainty",
        "risk",
        "risks",
        "risky",
        "threat",
        "threats",
        "threaten",
        "threatened",
    ]

    # Count matches (case-insensitive word boundaries for better matching)
    import re

    text_lower = text.lower()
    text_words = set(re.findall(r"\b\w+\b", text_lower))

    # Use word boundary matching for more precise pattern matching
    bullish_count = sum(
        1
        for pattern in bullish_patterns
        if pattern.lower() in text_words
        or re.search(r"\b" + re.escape(pattern.lower()) + r"\b", text_lower)
    )
    bearish_count = sum(
        1
        for pattern in bearish_patterns
        if pattern.lower() in text_words
        or re.search(r"\b" + re.escape(pattern.lower()) + r"\b", text_lower)
    )

    # Also check for negations that flip sentiment (e.g., "not increase" = bearish)
    negation_words = [
        "not",
        "no",
        "never",
        "neither",
        "nobody",
        "none",
        "nothing",
        "nowhere",
        "without",
        "lack",
        "lacks",
        "lacking",
    ]
    for negation in negation_words:
        if negation in text:
            # Check if negation is near bullish/bearish terms
            negation_pos = text.find(negation)
            for _i, pattern in enumerate(bullish_patterns):
                pattern_pos = text.find(pattern.lower())
                if pattern_pos != -1 and abs(pattern_pos - negation_pos) < 20:  # Within 20 chars
                    bearish_count += 1
                    bullish_count = max(0, bullish_count - 1)
            for _i, pattern in enumerate(bearish_patterns):
                pattern_pos = text.find(pattern.lower())
                if pattern_pos != -1 and abs(pattern_pos - negation_pos) < 20:  # Within 20 chars
                    bullish_count += 1
                    bearish_count = max(0, bearish_count - 1)

    # Context-aware adjustments based on market question
    if "increase" in question_lower or "rise" in question_lower:
        # Market is asking about increase - bullish = supports increase
        if "increase" in text or "rise" in text or "higher" in text:
            bullish_count += 2
        if "decrease" in text or "fall" in text or "lower" in text:
            bearish_count += 2
    elif "decrease" in question_lower or "fall" in question_lower or "cut" in question_lower:
        # Market is asking about decrease - bullish = supports decrease
        if "decrease" in text or "cut" in text or "lower" in text:
            bullish_count += 2
        if "increase" in text or "rise" in text or "hike" in text:
            bearish_count += 2
    elif "fed" in question_lower or "interest rate" in question_lower:
        # Fed/rate markets - context matters
        if "cut" in text or "lower" in text or "dovish" in text:
            bullish_count += 2
        if "hike" in text or "raise" in text or "hawkish" in text:
            bearish_count += 2

    # Consider signal direction if available
    if signal_direction == "up":
        # Signal suggests price should go up - articles supporting YES are more bullish
        bullish_count += 1
    elif signal_direction == "down":
        # Signal suggests price should go down - articles supporting NO are more bearish
        bearish_count += 1

    # Consider current price position
    # If YES price is very low (< 0.1), bullish news is more significant
    # If YES price is very high (> 0.9), bearish news is more significant
    if yes_price < 0.1:
        bullish_count = int(bullish_count * 1.2)  # Boost bullish significance
    elif yes_price > 0.9:
        bearish_count = int(bearish_count * 1.2)  # Boost bearish significance

    # Determine sentiment - require at least 1 match to be non-neutral
    # If both counts are 0 or equal, default to neutral
    sentiment = "neutral"
    if bullish_count > bearish_count and bullish_count >= 1:
        sentiment = "bullish"
    elif bearish_count > bullish_count and bearish_count >= 1:
        sentiment = "bearish"
    # If counts are equal and both > 0, default to neutral (conflicting signals)
    elif bullish_count == bearish_count and bullish_count > 0:
        sentiment = "neutral"
    # If both counts are 0, definitely neutral
    elif bullish_count == 0 and bearish_count == 0:
        sentiment = "neutral"

    # Debug logging (will only show if DEBUG level is enabled)
    logger.debug(
        "Sentiment analysis result",
        title=article.get("title", "")[:50],
        bullish_count=bullish_count,
        bearish_count=bearish_count,
        sentiment=sentiment,
        has_content=bool(content),
        text_length=len(text),
    )

    return sentiment


def analyze_articles_sentiment(
    articles: list[Dict[str, Any]],
    market_question: str,
    yes_price: float,
    signal_direction: Optional[str] = None,
    outcomes: Optional[list[str]] = None,
) -> list[Dict[str, Any]]:
    """Analyze sentiment for a list of articles and add sentiment field.

    Args:
        articles: List of article dicts
        market_question: The market question
        yes_price: Current YES price
        signal_direction: Optional signal direction
        outcomes: Optional list of outcomes

    Returns:
        List of articles with sentiment field added
    """
    enriched = []
    for article in articles:
        sentiment = analyze_article_sentiment(
            article=article,
            market_question=market_question,
            yes_price=yes_price,
            signal_direction=signal_direction,
            outcomes=outcomes,
        )
        # Create new dict with sentiment added
        enriched_article = {**article, "sentiment": sentiment}
        enriched.append(enriched_article)

    return enriched
