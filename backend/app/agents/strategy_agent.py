"""Strategy agent - evaluates signals and makes trading decisions."""

from __future__ import annotations

from typing import Any, Dict

from app.agents.state import AgentState
from app.core.logging_config import get_logger
from app.schemas.api import Signal

logger = get_logger(__name__)

CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


def _preset_defaults(preset: str) -> Dict[str, Any]:
    """Return default strategy parameters for a given risk preset."""
    preset = (preset or "Balanced").lower()

    if preset == "conservative" or preset == "cautious":
        return {
            "min_edge_pct": 0.08,
            "min_confidence": "high",
            "max_capital_pct": 0.08,
            "max_kelly_fraction": 0.15,
            "risk_off": False,
        }
    if preset == "aggressive":
        return {
            "min_edge_pct": 0.03,
            "min_confidence": "low",
            "max_capital_pct": 0.25,
            "max_kelly_fraction": 0.5,
            "risk_off": False,
        }

    return {
        "min_edge_pct": 0.05,
        "min_confidence": "medium",
        "max_capital_pct": 0.15,
        "max_kelly_fraction": 0.25,
        "risk_off": False,
    }


def decide_action(signal: Signal, state: AgentState, params: dict[str, Any]) -> Signal:
    """Decide trading action based on signal, position, and strategy parameters.

    Args:
        signal: Signal model with probabilities and Kelly fractions
        state: Agent state with current position info
        params: Strategy parameters (min_edge_pct, min_confidence, max_capital_pct, etc.)

    Returns:
        Updated Signal model with recommended_action, recommended_size_fraction, and targets
    """
    p_mkt = signal.market_prob
    # p_model is not currently used but kept for potential future use
    _p_model = signal.model_prob
    edge = signal.edge_pct
    kelly_yes = signal.kelly_fraction_yes
    kelly_no = signal.kelly_fraction_no

    pos_side = state.get("position_side", "flat")
    pos_size = state.get("position_size_fraction", 0.0)

    # 1) Check risk_off flag
    if params.get("risk_off", False):
        signal.recommended_action = "hold"
        signal.recommended_size_fraction = 0.0
        return signal

    # 2) Check confidence threshold
    conf_order = CONFIDENCE_ORDER
    min_confidence_param = params.get("min_confidence", "medium")
    min_conf_order = conf_order.get(min_confidence_param, 1)
    signal_conf_order = conf_order.get(signal.confidence_level, 0)

    logger.debug(
        "Confidence check",
        signal_confidence=signal.confidence_level,
        signal_conf_order=signal_conf_order,
        min_confidence=min_confidence_param,
        min_conf_order=min_conf_order,
        will_hold=signal_conf_order < min_conf_order,
    )

    if signal_conf_order < min_conf_order:
        logger.info(
            "Signal confidence below minimum threshold - holding",
            signal_confidence=signal.confidence_level,
            min_confidence=min_confidence_param,
            signal_conf_order=signal_conf_order,
            min_conf_order=min_conf_order,
        )
        signal.recommended_action = "hold"
        signal.recommended_size_fraction = 0.0
        return signal

    # 3) Check edge threshold
    if abs(edge) < params.get("min_edge_pct", 0.05):
        signal.recommended_action = "hold"
        signal.recommended_size_fraction = 0.0
        return signal

    # 4) Determine raw Kelly recommendation (on YES or NO)
    if edge > 0:  # BUY YES
        raw_fraction = max(0.0, kelly_yes)
        side = "long_yes"
    else:  # BUY NO (edge < 0)
        raw_fraction = max(0.0, kelly_no)
        side = "long_no"

    # 5) Clamp with strategy limits
    kelly_cap = params.get("max_kelly_fraction", 0.25)
    max_capital = params.get("max_capital_pct", 0.15)

    target_fraction = min(raw_fraction * kelly_cap, max_capital)

    # 6) Compare with current position
    if pos_side == side:
        # Already in the same direction; decide whether to add, reduce, or hold
        if target_fraction > pos_size:
            signal.recommended_action = "buy_yes" if side == "long_yes" else "buy_no"
            signal.recommended_size_fraction = round(target_fraction - pos_size, 4)
        elif target_fraction < pos_size:
            signal.recommended_action = "reduce_yes" if side == "long_yes" else "reduce_no"
            signal.recommended_size_fraction = round(pos_size - target_fraction, 4)
        else:
            signal.recommended_action = "hold"
            signal.recommended_size_fraction = 0.0
    elif pos_side == "flat":
        # Flat position - enter if target > 0
        if target_fraction > 0:
            signal.recommended_action = "buy_yes" if side == "long_yes" else "buy_no"
            signal.recommended_size_fraction = round(target_fraction, 4)
        else:
            signal.recommended_action = "hold"
            signal.recommended_size_fraction = 0.0
    else:
        # Different direction - need to close current position first
        # For now, just hold (could implement position reversal logic later)
        signal.recommended_action = "hold"
        signal.recommended_size_fraction = 0.0

    # 7) Set basic targets (simple rules to start)
    if edge > 0:
        # Long YES: take profit when market moves up, stop loss when it moves down
        signal.target_take_profit_prob = round(p_mkt + edge * 0.8, 4)  # Grab most of the edge
        signal.target_stop_loss_prob = round(p_mkt - edge * 0.5, 4)  # Cut halfway against you
    elif edge < 0:
        # Long NO: take profit when market moves down, stop loss when it moves up
        # Market moves down (edge is negative)
        signal.target_take_profit_prob = round(p_mkt + edge * 0.8, 4)
        signal.target_stop_loss_prob = round(p_mkt - edge * 0.5, 4)  # Market moves up
    else:
        signal.target_take_profit_prob = None
        signal.target_stop_loss_prob = None

    return signal


async def run_strategy_agent(state: AgentState) -> AgentState:
    """Evaluate the model signal and turn it into a concrete decision.

    This agent must run after prob_agent since it needs the signal.
    Uses decide_action to compute recommendations and update the signal.
    """
    preset = state.get("strategy_preset") or "Balanced"
    logger.debug("Running strategy agent", preset=preset)
    horizon = state.get("horizon") or "24h"

    preset_base = _preset_defaults(preset)
    user_overrides = state.get("strategy_params", {}) or {}
    
    # Ensure min_confidence from config is always applied (enforces Minimum Confidence configuration)
    # Priority: user_overrides (explicit strategy_params) > config > preset defaults
    config = state.get("config", {}) or {}
    if "min_confidence" in config:
        # Config's min_confidence should override preset defaults, but not explicit user overrides
        if "min_confidence" not in user_overrides:
            user_overrides = {**user_overrides, "min_confidence": config["min_confidence"]}
            logger.debug(
                "Applied min_confidence from config",
                min_confidence=config["min_confidence"],
                preset=preset,
            )
        else:
            logger.debug(
                "Using min_confidence from strategy_params (overrides config)",
                min_confidence=user_overrides["min_confidence"],
                config_min_confidence=config.get("min_confidence"),
            )
    
    params = {**preset_base, **user_overrides}

    state["strategy_preset"] = preset
    state["horizon"] = horizon
    state["strategy_params"] = params

    # Get signal - handle both Pydantic model and dict for backward compatibility
    signal_raw = state.get("signal")

    if signal_raw is None:
        logger.warning("No signal found in state, creating empty signal")
        # Create a minimal signal for backward compatibility
        from app.core.signal_utils import infer_market_prob

        snapshot = state.get("market_snapshot", {}) or {}
        p_mkt = infer_market_prob(snapshot)
        signal = Signal(
            market_prob=p_mkt,
            model_prob=p_mkt,
            edge_pct=0.0,
            expected_value_per_dollar=0.0,
            kelly_fraction_yes=0.0,
            kelly_fraction_no=0.0,
            confidence_level="low",
            confidence_score=0.0,
            recommended_action="hold",
            recommended_size_fraction=0.0,
            target_take_profit_prob=None,
            target_stop_loss_prob=None,
            horizon=horizon,
            rationale_short="No signal available",
            rationale_long=None,
        )
    elif isinstance(signal_raw, Signal):
        # Already a Pydantic model
        signal = signal_raw
    elif isinstance(signal_raw, dict):
        # Legacy dict format - try to convert to Signal model
        # This handles backward compatibility
        try:
            # Extract fields from dict, with defaults
            p_mkt = signal_raw.get("market_prob") or signal_raw.get("yes_price", 0.5)
            p_model = signal_raw.get("model_prob_abs") or signal_raw.get("model_prob", 0.0)
            if isinstance(p_model, float) and abs(p_model) < 1.0:
                # Might be a delta, convert to absolute
                p_model = p_mkt + p_model
            p_model = max(0.0, min(1.0, p_model))

            from app.core.signal_utils import (
                compute_edge_and_ev,
                estimate_confidence,
                kelly_fraction_no,
                kelly_fraction_yes,
            )

            edge, ev = compute_edge_and_ev(p_model, p_mkt)
            kelly_yes = kelly_fraction_yes(p_model, p_mkt)
            kelly_no = kelly_fraction_no(p_model, p_mkt)
            news_ctx = state.get("news_context", {}) or {}
            conf_level, conf_score = estimate_confidence(news_ctx, p_model, p_mkt)

            signal = Signal(
                market_prob=round(p_mkt, 4),
                model_prob=round(p_model, 4),
                edge_pct=round(edge, 4),
                expected_value_per_dollar=round(ev, 4),
                kelly_fraction_yes=round(kelly_yes, 4),
                kelly_fraction_no=round(kelly_no, 4),
                confidence_level=signal_raw.get("confidence", conf_level),
                confidence_score=conf_score,
                recommended_action="hold",
                recommended_size_fraction=0.0,
                target_take_profit_prob=None,
                target_stop_loss_prob=None,
                horizon=horizon,
                rationale_short=signal_raw.get("rationale", ""),
                rationale_long=None,
            )
        except Exception as exc:
            logger.warning(
                "Error converting dict signal to Signal model",
                error=str(exc),
                exc_info=True,
            )
            # Fallback: create minimal signal
            from app.core.signal_utils import infer_market_prob

            snapshot = state.get("market_snapshot", {}) or {}
            p_mkt = infer_market_prob(snapshot)
            signal = Signal(
                market_prob=p_mkt,
                model_prob=p_mkt,
                edge_pct=0.0,
                expected_value_per_dollar=0.0,
                kelly_fraction_yes=0.0,
                kelly_fraction_no=0.0,
                confidence_level="low",
                confidence_score=0.0,
                recommended_action="hold",
                recommended_size_fraction=0.0,
                target_take_profit_prob=None,
                target_stop_loss_prob=None,
                horizon=horizon,
                rationale_short="Signal conversion failed",
                rationale_long=None,
            )
    else:
        logger.warning("Unexpected signal type", signal_type=type(signal_raw).__name__)
        # Fallback
        from app.core.signal_utils import infer_market_prob

        snapshot = state.get("market_snapshot", {}) or {}
        p_mkt = infer_market_prob(snapshot)
        signal = Signal(
            market_prob=p_mkt,
            model_prob=p_mkt,
            edge_pct=0.0,
            expected_value_per_dollar=0.0,
            kelly_fraction_yes=0.0,
            kelly_fraction_no=0.0,
            confidence_level="low",
            confidence_score=0.0,
            recommended_action="hold",
            recommended_size_fraction=0.0,
            target_take_profit_prob=None,
            target_stop_loss_prob=None,
            horizon=horizon,
            rationale_short="Invalid signal type",
            rationale_long=None,
        )

    # Apply decision logic
    signal = decide_action(signal, state, params)

    # Update state with updated signal
    state["signal"] = signal

    # Also create legacy decision dict for backward compatibility
    action_map = {
        "buy_yes": "BUY",
        "buy_no": "BUY",
        "reduce_yes": "SELL",
        "reduce_no": "SELL",
        "hold": "HOLD",
    }
    action = action_map.get(signal.recommended_action, "HOLD")

    notes = (
        f"Action: {signal.recommended_action}, size: {signal.recommended_size_fraction:.4f}. "
        f"Edge: {signal.edge_pct:.4f}, confidence: {signal.confidence_level}."
    )

    state["decision"] = {
        "action": action,
        "side": "YES" if "yes" in signal.recommended_action else "NO",
        "edge_pct": round(signal.edge_pct, 4),
        "toy_kelly_fraction": round(signal.recommended_size_fraction, 4),
        "notes": notes,
    }

    logger.info(
        "signal_decision",
        market_slug=state.get("slug", "unknown"),
        recommended_action=signal.recommended_action,
        recommended_size_fraction=round(signal.recommended_size_fraction, 4),
        edge=round(signal.edge_pct, 4),
        confidence_level=signal.confidence_level,
    )

    return state
