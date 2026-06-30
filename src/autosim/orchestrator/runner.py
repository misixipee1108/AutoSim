"""Simulation orchestration: single trial and multi-trial iteration."""

from __future__ import annotations

from autosim.agent.deepseek import AgentService
from autosim.schemas import AgentAction, AgentDecision, ProbeSnapshot, SimInput, TrialResult
from autosim.simulator.falling_block import simulate_falling_block


def run_trial(sim_input: SimInput, trial_index: int = 0) -> TrialResult:
    agent = AgentService(sim_input.agent)
    probe_history: list[ProbeSnapshot] = []

    def on_probe(probe: ProbeSnapshot) -> AgentDecision | None:
        probe_history.append(probe)
        decision = agent.evaluate_mid_run(probe, sim_input, probe_history)
        if decision.action == AgentAction.EARLY_STOP:
            return decision
        return None

    result = simulate_falling_block(
        sim_input,
        on_probe=on_probe,
        trial_index=trial_index,
    )

    post_decision = agent.evaluate_post_run(
        sim_input,
        result.probes,
        result.early_stopped,
        result.stop_reason,
    )
    result.decisions.append(post_decision)
    return result


def run_iteration(base_input: SimInput) -> list[TrialResult]:
    results: list[TrialResult] = []
    current_input = base_input
    max_trials = base_input.iteration.max_trials

    for trial_idx in range(max_trials):
        result = run_trial(current_input, trial_index=trial_idx)
        results.append(result)

        post_decisions = [
            d for d in result.decisions if d.action == AgentAction.RECOMMEND_NEXT
        ]
        if not post_decisions:
            if base_input.iteration.stop_on == "recommend_next":
                break
            continue

        last_decision = post_decisions[-1]
        if not last_decision.suggested_params:
            if base_input.iteration.stop_on == "recommend_next":
                break
            continue

        current_input = current_input.model_copy_with_params(last_decision.suggested_params)

    return results
