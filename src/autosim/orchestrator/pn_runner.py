"""PN junction simulation orchestration."""

from __future__ import annotations

from autosim.agent.pn_deepseek import PnAgentService
from autosim.pn.bias_sweep import run_bias_sweep
from autosim.pn.schemas import (
    PnAgentAction,
    PnAgentDecision,
    PnNewtonProbe,
    PnSimInput,
    PnSweepResult,
    PnTrialResult,
)
from autosim.pn.solve import solve_pn


def _make_on_probe(
    agent: PnAgentService,
    sim_input: PnSimInput,
    probe_history: list[PnNewtonProbe],
    decisions: list[PnAgentDecision],
):
    def on_probe(probe: PnNewtonProbe) -> PnAgentDecision | None:
        probe_history.append(probe)
        decision = agent.evaluate_mid_run(probe, sim_input, probe_history)
        if decision.action in (
            PnAgentAction.EARLY_STOP,
            PnAgentAction.ADJUST_DAMPING,
            PnAgentAction.INCREASE_DAMPING,
            PnAgentAction.CHANGE_INITIAL_GUESS,
            PnAgentAction.REFINE_MESH,
            PnAgentAction.SWITCH_SOLVER,
            PnAgentAction.ADJUST_BIAS_STEP,
            PnAgentAction.REDUCE_BIAS_STEP,
            PnAgentAction.MARK_AS_INFEASIBLE,
        ):
            return decision
        if decision.action == PnAgentAction.CONTINUE:
            decisions.append(decision)
        return None

    return on_probe


def run_pn_trial(
    sim_input: PnSimInput,
    trial_index: int = 0,
    max_mesh_restarts: int = 2,
) -> PnTrialResult:
    agent = PnAgentService(sim_input.agent)
    current_input = sim_input
    all_decisions: list[PnAgentDecision] = []
    result: PnTrialResult | None = None

    for _ in range(max_mesh_restarts + 1):
        probe_history: list[PnNewtonProbe] = []
        trial_decisions: list[PnAgentDecision] = []
        on_probe = _make_on_probe(agent, current_input, probe_history, trial_decisions)

        result = solve_pn(current_input, on_probe=on_probe, trial_index=trial_index)
        all_decisions.extend(trial_decisions)
        all_decisions.extend(result.decisions)
        result.decisions = all_decisions

        if result.stop_reason not in ("mesh_restart_requested", "solver_switch_requested"):
            break

        restart_decisions = [
            d for d in all_decisions
            if d.action in (
                PnAgentAction.CHANGE_INITIAL_GUESS,
                PnAgentAction.REFINE_MESH,
                PnAgentAction.SWITCH_SOLVER,
            )
            and d.suggested_params
        ]
        if not restart_decisions:
            params: dict = {"Nx": int(current_input.Nx * 1.5)}
            params["junction_refinement"] = {
                "enabled": True,
                "ratio": current_input.junction_refinement.ratio,
            }
            if result.stop_reason == "solver_switch_requested":
                params["solver"] = {"method": "newton_line_search"}
            current_input = current_input.model_copy_with_params(params)
            continue
        params = dict(restart_decisions[-1].suggested_params or {})
        if "Nx" not in params and result.stop_reason == "mesh_restart_requested":
            params["Nx"] = int(current_input.Nx * 1.5)
        if result.stop_reason == "solver_switch_requested" and "solver" not in params:
            params["solver"] = {"method": "newton_line_search"}
        current_input = current_input.model_copy_with_params(params)

    assert result is not None
    post_decision = agent.evaluate_post_run(
        current_input, result.probes, result.converged, result.stop_reason
    )
    result.decisions.append(post_decision)
    result.input = current_input
    return result


def run_pn_with_sweep(sim_input: PnSimInput) -> tuple[list[PnTrialResult], PnSweepResult]:
    if sim_input.bias_scan.enabled:
        return run_bias_sweep(sim_input)
    result = run_pn_trial(sim_input)
    return [result], PnSweepResult(points=[])


def run_pn_iteration(base_input: PnSimInput) -> list[PnTrialResult]:
    results: list[PnTrialResult] = []
    current_input = base_input
    max_trials = base_input.iteration.max_trials

    for trial_idx in range(max_trials):
        if current_input.bias_scan.enabled and trial_idx == 0:
            sweep_results, _ = run_bias_sweep(current_input)
            results.extend(sweep_results)
        else:
            result = run_pn_trial(current_input, trial_index=trial_idx)
            results.append(result)

        last_result = results[-1]
        post_decisions = [
            d for d in last_result.decisions
            if d.action == PnAgentAction.RECOMMEND_NEXT_PARAMETERS
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
        current_input.bias_scan.enabled = False

    return results
