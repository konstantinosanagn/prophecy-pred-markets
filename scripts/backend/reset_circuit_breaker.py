#!/usr/bin/env python
"""Reset the OpenAI circuit breaker to allow API calls again."""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.resilience import openai_circuit


def reset_circuit_breaker():
    """Reset the OpenAI circuit breaker."""
    print(f"Current circuit breaker state: {openai_circuit.state.value}")
    print(f"Failure count: {openai_circuit.failure_count}")

    openai_circuit.reset()

    print("\nCircuit breaker reset!")
    print(f"New state: {openai_circuit.state.value}")
    print(f"Failure count: {openai_circuit.failure_count}")
    print("\nThe circuit breaker is now CLOSED and will allow API calls.")


if __name__ == "__main__":
    reset_circuit_breaker()
