"""Tests for Phased Analysis."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.schemas import AnalyzeRequest
from app.services.phased_analysis import run_analysis_for_run_id


@pytest.mark.anyio(backend="asyncio")
async def test_run_analysis_for_run_id_full_flow():
    """Test run_analysis_for_run_id full analysis flow."""
    req = AnalyzeRequest(
        market_url="https://polymarket.com/market/test",
        horizon="24h",
        strategy_preset="Balanced",
    )

    with (
        patch("app.services.phased_analysis.run_market_agent") as mock_market,
        patch("app.services.phased_analysis.run_event_agent") as mock_event,
        patch("app.services.phased_analysis.run_tavily_prompt_agent") as mock_tavily,
        patch("app.services.phased_analysis.run_news_agent") as mock_news,
        patch("app.services.phased_analysis.run_news_summary_agent") as mock_summary,
        patch("app.services.phased_analysis.run_prob_agent") as mock_prob,
        patch("app.services.phased_analysis.run_strategy_agent") as mock_strategy,
        patch("app.services.phased_analysis.run_report_agent") as mock_report,
        patch("app.services.phased_analysis.update_run_phase_async") as mock_update,
        patch(
            "app.services.phased_analysis.update_run_with_event_and_market_async"
        ) as mock_update_ids,
        patch("app.services.phased_analysis.persist_run_snapshot_async") as mock_persist,
    ):
        # Setup mocks
        state = {
            "run_id": "test-run",
            "market_snapshot": {},
            "event_context": {},
            "news_context": {},
            "signal": {},
            "decision": {},
            "report": {},
        }
        mock_market.return_value = state
        mock_event.return_value = state
        mock_tavily.return_value = state
        mock_news.return_value = state
        mock_summary.return_value = state
        mock_prob.return_value = state
        mock_strategy.return_value = state
        mock_report.return_value = state
        mock_update.return_value = AsyncMock()
        mock_update_ids.return_value = AsyncMock()
        mock_persist.return_value = AsyncMock()

        await run_analysis_for_run_id("test-run", req)

        # Verify all phases were called
        assert mock_market.called
        assert mock_event.called
        assert mock_tavily.called
        assert mock_news.called
        assert mock_summary.called
        assert mock_prob.called
        assert mock_strategy.called
        assert mock_report.called


@pytest.mark.anyio(backend="asyncio")
async def test_run_analysis_for_run_id_market_selection():
    """Test run_analysis_for_run_id with market selection required."""
    req = AnalyzeRequest(
        market_url="https://polymarket.com/event/test",
    )

    with (
        patch("app.services.phased_analysis.run_market_agent") as mock_market,
        patch("app.services.phased_analysis.run_event_agent") as mock_event,
        patch("app.services.phased_analysis.update_run_phase_async") as mock_update,
    ):
        state = {
            "run_id": "test-run",
            "requires_market_selection": True,
            "market_options": [{"slug": "market-1"}],
            "event_context": {},
        }
        mock_market.return_value = state
        mock_event.return_value = state
        mock_update.return_value = AsyncMock()

        await run_analysis_for_run_id("test-run", req)

        # Should stop early
        assert mock_update.called
        # Should not continue to other phases


@pytest.mark.anyio(backend="asyncio")
async def test_run_analysis_for_run_id_error_handling():
    """Test run_analysis_for_run_id error handling."""
    req = AnalyzeRequest(
        market_url="https://polymarket.com/market/test",
    )

    with patch("app.services.phased_analysis.run_market_agent") as mock_market:
        mock_market.side_effect = Exception("Market agent error")

        with patch("app.services.phased_analysis.update_run_phase_async") as mock_update:
            mock_update.return_value = AsyncMock()

            with pytest.raises(RuntimeError):
                await run_analysis_for_run_id("test-run", req)

            # Should mark phases as error
            assert mock_update.called


@pytest.mark.anyio(backend="asyncio")
async def test_run_analysis_for_run_id_phase_updates():
    """Test run_analysis_for_run_id phase updates."""
    req = AnalyzeRequest(
        market_url="https://polymarket.com/market/test",
    )

    with (
        patch("app.services.phased_analysis.run_market_agent") as mock_market,
        patch("app.services.phased_analysis.run_event_agent") as mock_event,
        patch("app.services.phased_analysis.run_tavily_prompt_agent") as mock_tavily,
        patch("app.services.phased_analysis.run_news_agent") as mock_news,
        patch("app.services.phased_analysis.run_news_summary_agent") as mock_summary,
        patch("app.services.phased_analysis.run_prob_agent") as mock_prob,
        patch("app.services.phased_analysis.run_strategy_agent") as mock_strategy,
        patch("app.services.phased_analysis.run_report_agent") as mock_report,
        patch("app.services.phased_analysis.update_run_phase_async") as mock_update,
        patch(
            "app.services.phased_analysis.update_run_with_event_and_market_async"
        ) as mock_update_ids,
        patch("app.services.phased_analysis.persist_run_snapshot_async") as mock_persist,
    ):
        state = {
            "run_id": "test-run",
            "market_snapshot": {},
            "event_context": {},
            "news_context": {},
            "signal": {},
            "decision": {},
            "report": {},
        }
        mock_market.return_value = state
        mock_event.return_value = state
        mock_tavily.return_value = state
        mock_news.return_value = state
        mock_summary.return_value = state
        mock_prob.return_value = state
        mock_strategy.return_value = state
        mock_report.return_value = state
        mock_update.return_value = AsyncMock()
        mock_update_ids.return_value = AsyncMock()
        mock_persist.return_value = AsyncMock()

        await run_analysis_for_run_id("test-run", req)

        # Should update phases
        assert mock_update.call_count >= 3  # market, news, signal, report
