"""Tests for orchestrator and agent integration."""

from unittest.mock import MagicMock, patch

import pytest

from autosim.agent.deepseek import AgentService
from autosim.agent.rules import RulesAgent
from autosim.orchestrator.runner import run_iteration, run_trial
from autosim.schemas import AgentAction, AgentBackend, AgentConfig, AgentDecision, SimInput


@pytest.fixture
def base_input():
    return SimInput(
        drag_model="quadratic",
        drag_params={"c2": 0.5},
        y0=100.0,
        agent=AgentConfig(backend=AgentBackend.RULES),
        iteration={"max_trials": 3, "stop_on": "recommend_next"},
    )


def test_run_trial_completes(base_input):
    result = run_trial(base_input)
    assert result.impact_time is not None
    assert len(result.probes) > 0
    assert len(result.decisions) >= 1


def test_run_iteration_multiple_trials(base_input):
    results = run_iteration(base_input)
    assert len(results) >= 1
    assert len(results) <= 3


def test_rules_agent_early_stop_on_nan():
    from autosim.schemas import ProbeSnapshot

    agent = RulesAgent(AgentConfig())
    probe = ProbeSnapshot(
        t=1.0,
        y=50.0,
        v=float("nan"),
        a=0.0,
        ke=0.0,
        pe=0.0,
        energy_drift=0.0,
        distance_to_ground=50.0,
        is_diverging=True,
        is_nan=True,
        drag_force=0.0,
    )
    decision = agent.evaluate_mid_run(probe, SimInput())
    assert decision.action == AgentAction.EARLY_STOP


def test_deepseek_json_parsing():
    agent = AgentService(AgentConfig(backend=AgentBackend.DEEPSEEK))
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"action": "continue", "reason": "ok", "confidence": 0.9}'
                }
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"}):
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            decision = agent._call_llm(
                SimInput(),
                [],
                phase="mid_run",
            )
    assert decision.action == AgentAction.CONTINUE
    assert decision.confidence == 0.9
