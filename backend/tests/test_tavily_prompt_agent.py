"""Tests for Tavily Prompt Agent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.state import AgentState
from app.agents.tavily_prompt_agent import (
    build_prompt_from_state,
    parse_tavily_specs,
    run_tavily_prompt_agent,
)


def test_parse_tavily_specs_happy_path():
    """Test parsing valid Tavily query specs from LLM response."""
    raw_json = {
        "queries": [
            {
                "name": "latest_developments",
                "query": "Recent news in the last 24 hours about Fed interest rate decision",
                "max_results": 8,
                "search_depth": "advanced",
                "timeframe": "24h",
            },
            {
                "name": "fundamentals",
                "query": "Background and long-term factors influencing Fed policy",
                "max_results": 10,
                "search_depth": "basic",
            },
        ]
    }

    specs = parse_tavily_specs(raw_json)

    assert len(specs) == 2
    assert specs[0]["name"] == "latest_developments"
    assert specs[0]["query"] == "Recent news in the last 24 hours about Fed interest rate decision"
    assert specs[0]["max_results"] == 8
    assert specs[0]["search_depth"] == "advanced"
    assert specs[0]["timeframe"] == "24h"

    assert specs[1]["name"] == "fundamentals"
    assert specs[1]["max_results"] == 10
    assert specs[1]["search_depth"] == "basic"
    assert "timeframe" not in specs[1]


def test_parse_tavily_specs_invalid_query_skipped():
    """Test that invalid query specs (missing query) are skipped."""
    raw_json = {
        "queries": [
            {
                "name": "valid_query",
                "query": "Valid query string",
                "max_results": 8,
            },
            {
                "name": "invalid_query",
                # Missing "query" field
                "max_results": 8,
            },
        ]
    }

    specs = parse_tavily_specs(raw_json)

    assert len(specs) == 1
    assert specs[0]["name"] == "valid_query"
    assert specs[0]["query"] == "Valid query string"


def test_parse_tavily_specs_defaults_applied():
    """Test that default values are applied for missing fields."""
    raw_json = {
        "queries": [
            {
                "query": "Just a query string",
                # Missing name, max_results, search_depth
            }
        ]
    }

    specs = parse_tavily_specs(raw_json)

    assert len(specs) == 1
    assert specs[0]["name"] == "news"  # Default name
    assert specs[0]["max_results"] == 8  # Default max_results
    assert specs[0]["search_depth"] == "basic"  # Default search_depth


def test_parse_tavily_specs_max_results_clamped():
    """Test that max_results is clamped between 5 and 12."""
    raw_json = {
        "queries": [
            {"query": "Query 1", "max_results": 3},  # Below minimum
            {"query": "Query 2", "max_results": 15},  # Above maximum
            {"query": "Query 3", "max_results": 8},  # Valid
        ]
    }

    specs = parse_tavily_specs(raw_json)

    assert len(specs) == 3
    assert specs[0]["max_results"] == 5  # Clamped to minimum
    assert specs[1]["max_results"] == 12  # Clamped to maximum
    assert specs[2]["max_results"] == 8  # Unchanged


def test_parse_tavily_specs_empty_list():
    """Test parsing empty queries list."""
    raw_json = {"queries": []}
    specs = parse_tavily_specs(raw_json)
    assert len(specs) == 0


def test_parse_tavily_specs_missing_queries_field():
    """Test parsing response with missing queries field."""
    raw_json = {}
    specs = parse_tavily_specs(raw_json)
    assert len(specs) == 0


def test_build_prompt_from_state_full_state():
    """Test build_prompt_from_state with full state and all fields."""
    state: AgentState = {
        "market_snapshot": {
            "question": "Will this test pass?",
            "outcomes": ["Yes", "No"],
        },
        "event_context": {
            "category": "Macro",
            "region": "US",
            "resolution_criteria": "Test criteria",
        },
        "event": {
            "category": "Macro",
        },
        "horizon": "48h",
        "strategy_preset": "Aggressive",
    }

    prompt = build_prompt_from_state(state)

    assert "Will this test pass?" in prompt
    assert "Yes" in prompt or "No" in prompt
    assert "Macro" in prompt
    assert "48h" in prompt
    assert "Aggressive" in prompt


def test_build_prompt_from_state_missing_fields():
    """Test build_prompt_from_state with missing fields (fallbacks)."""
    state: AgentState = {}

    prompt = build_prompt_from_state(state)

    assert "Market snapshot:" in prompt
    assert "Analysis horizon:" in prompt
    assert "Strategy preset:" in prompt


def test_build_prompt_from_state_various_configurations():
    """Test build_prompt_from_state with various event/market configurations."""
    # Test with event_context only
    state1: AgentState = {
        "event_context": {
            "category": "Politics",
            "region": "EU",
        },
    }
    prompt1 = build_prompt_from_state(state1)
    assert "Politics" in prompt1
    assert "EU" in prompt1

    # Test with event doc only
    state2: AgentState = {
        "event": {
            "category": "Sports",
        },
    }
    prompt2 = build_prompt_from_state(state2)
    assert "Sports" in prompt2


@pytest.mark.anyio(backend="asyncio")
async def test_run_tavily_prompt_agent_with_openai():
    """Test run_tavily_prompt_agent with OpenAI available."""
    state: AgentState = {
        "slug": "test-market",
        "horizon": "24h",
        "strategy_preset": "Balanced",
        "market_snapshot": {
            "question": "Will this test pass?",
        },
        "event_context": {
            "title": "Test Event",
        },
    }

    mock_response = {
        "queries": [
            {
                "name": "test_query",
                "query": "Test query string",
                "max_results": 8,
                "search_depth": "basic",
            }
        ]
    }

    with patch("app.agents.tavily_prompt_agent.get_openai_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.api_key = "test-key"
        mock_client.client = MagicMock()
        mock_client._use_new_api = True

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_client.client.chat.completions.create = MagicMock(return_value=mock_completion)

        mock_get_client.return_value = mock_client

        # Mock the executor to return the parsed response
        # The function calls _generate_tavily_queries_sync which returns a dict
        # Then parse_tavily_specs processes it
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            # run_in_executor should call the function and return its result
            # Since we're mocking it, we return the mock_response directly
            mock_loop_instance.run_in_executor = AsyncMock(return_value=mock_response)
            mock_loop.return_value = mock_loop_instance

            result = await run_tavily_prompt_agent(state)

            assert "tavily_queries" in result
            assert len(result["tavily_queries"]) == 1
            assert result["tavily_queries"][0]["name"] == "test_query"


@pytest.mark.anyio(backend="asyncio")
async def test_run_tavily_prompt_agent_fallback():
    """Test run_tavily_prompt_agent with fallback scenarios."""
    state: AgentState = {
        "slug": "test-market",
        "horizon": "24h",
        "market_snapshot": {},
        "event_context": {},
    }

    with patch("app.agents.tavily_prompt_agent.get_openai_client") as mock_get_client:
        mock_get_client.side_effect = RuntimeError("OpenAI not available")

        result = await run_tavily_prompt_agent(state)

        # Should not set tavily_queries, let news_agent handle fallback
        assert "tavily_queries" not in result or result.get("tavily_queries") is None


@pytest.mark.anyio(backend="asyncio")
async def test_run_tavily_prompt_agent_missing_event_context():
    """Test run_tavily_prompt_agent with missing event_context."""
    state: AgentState = {
        "slug": "test-market",
        "horizon": "24h",
        "market_snapshot": {},
    }

    with patch("app.agents.tavily_prompt_agent.get_openai_client") as mock_get_client:
        mock_get_client.side_effect = RuntimeError("OpenAI not available")

        result = await run_tavily_prompt_agent(state)

        # Should still work without event_context
        assert result is not None


@pytest.mark.anyio(backend="asyncio")
async def test_run_tavily_prompt_agent_already_has_queries():
    """Test run_tavily_prompt_agent when tavily_queries already present."""
    state: AgentState = {
        "slug": "test-market",
        "tavily_queries": [
            {
                "name": "existing",
                "query": "Existing query",
                "max_results": 8,
                "search_depth": "basic",
            }
        ],
    }

    result = await run_tavily_prompt_agent(state)

    # Should skip generation and return as-is
    assert result["tavily_queries"] == state["tavily_queries"]


@pytest.mark.anyio(backend="asyncio")
async def test_run_tavily_prompt_agent_invalid_json():
    """Test run_tavily_prompt_agent with invalid JSON response."""
    state: AgentState = {
        "slug": "test-market",
        "horizon": "24h",
        "market_snapshot": {},
        "event_context": {},
    }

    with patch("app.agents.tavily_prompt_agent.get_openai_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.api_key = "test-key"
        mock_get_client.return_value = mock_client

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = MagicMock(
                side_effect=ValueError("Invalid JSON")
            )

            result = await run_tavily_prompt_agent(state)

            # Should not set tavily_queries on error
            assert "tavily_queries" not in result or result.get("tavily_queries") is None


@pytest.mark.anyio(backend="asyncio")
async def test_run_tavily_prompt_agent_no_valid_queries():
    """Test run_tavily_prompt_agent when LLM generates no valid queries."""
    state: AgentState = {
        "slug": "test-market",
        "horizon": "24h",
        "market_snapshot": {},
        "event_context": {},
    }

    mock_response = {
        "queries": []  # Empty queries
    }

    with patch("app.agents.tavily_prompt_agent.get_openai_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.api_key = "test-key"
        mock_get_client.return_value = mock_client

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = MagicMock(return_value=mock_response)

            result = await run_tavily_prompt_agent(state)

            # Should not set tavily_queries when empty
            assert "tavily_queries" not in result or result.get("tavily_queries") is None


@pytest.mark.anyio(backend="asyncio")
async def test_run_tavily_prompt_agent_circuit_breaker():
    """Test run_tavily_prompt_agent with circuit breaker open."""
    state: AgentState = {
        "slug": "test-market",
        "horizon": "24h",
        "market_snapshot": {},
        "event_context": {},
    }

    with patch("app.agents.tavily_prompt_agent.get_openai_client") as mock_get_client:
        mock_get_client.side_effect = RuntimeError("Circuit breaker is OPEN")

        result = await run_tavily_prompt_agent(state)

        # Should not set tavily_queries
        assert "tavily_queries" not in result or result.get("tavily_queries") is None
