"""Tests for PN agent and orchestrator."""

from unittest.mock import MagicMock, patch

from autosim.agent.pn_deepseek import PnAgentService
from autosim.agent.pn_rules import PnRulesAgent
from autosim.orchestrator.pn_runner import run_pn_iteration, run_pn_trial
from autosim.pn.schemas import PnAgentAction, PnAgentConfig, PnNewtonProbe, PnSimInput
from autosim.schemas import AgentBackend


def test_pn_run_trial():
    sim_input = PnSimInput(
        Na=1e18, Nd=1e16, Nx=200, tol=5e-4, max_iter=200, damping=0.5,
        agent=PnAgentConfig(backend=AgentBackend.RULES),
    )
    result = run_pn_trial(sim_input)
    assert result.converged or result.stop_reason == "converged"
    assert len(result.probes) > 0
    assert result.Vbi_numeric is not None


def test_pn_run_iteration():
    sim_input = PnSimInput(
        Na=1e18, Nd=1e16, Nx=200, tol=1e-4, max_iter=80, damping=0.5,
        agent=PnAgentConfig(backend=AgentBackend.RULES),
        iteration={"max_trials": 2, "stop_on": "recommend_next"},
    )
    results = run_pn_iteration(sim_input)
    assert len(results) >= 1


def test_pn_rules_early_stop():
    agent = PnRulesAgent(PnAgentConfig())
    probe = PnNewtonProbe(
        iteration=1, residual_norm=1.0, residual_reduction_rate=1.0,
        delta_norm=0.1, damping_factor=0.5, jacobian_condition_estimate=1e6,
        max_psi=0.5, min_psi=-0.5, max_electric_field=1e4,
        max_carrier_density=1e18, min_n=float("nan"), min_p=1e10,
        charge_neutrality_error=0.0, is_nan=True, is_unphysical=False,
        exp_clamped=False, stalled=False, convergence_status="failed_nan",
    )
    decision = agent.evaluate_mid_run(probe, PnSimInput())
    assert decision.action == PnAgentAction.EARLY_STOP


def test_pn_deepseek_json_parsing():
    agent = PnAgentService(PnAgentConfig(backend=AgentBackend.DEEPSEEK))
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"action": "continue", "reason": "ok", "confidence": 0.9}'}}]
    }
    mock_response.raise_for_status = MagicMock()
    with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"}):
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            decision = agent._call_llm(PnSimInput(), [], "mid_run")
    assert decision.action == PnAgentAction.CONTINUE
