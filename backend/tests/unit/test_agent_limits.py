import pytest

from forge.application.agents import AgentConfig


@pytest.mark.parametrize(
    "limits",
    [
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": float("inf")},
        {"max_tokens": -1},
        {"max_cost_usd": 1},
        {"max_retries": 6},
        {"max_retries": 1.5},
        {"max_output_tokens": 0},
        {"input_cost_per_million": -1},
        {"output_cost_per_million": float("inf")},
    ],
)
def test_application_config_rejects_invalid_limits(limits: dict) -> None:
    with pytest.raises(ValueError):
        AgentConfig(instructions="Test", **limits)
