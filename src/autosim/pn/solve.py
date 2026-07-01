"""Unified physics model router for PN junction."""

from __future__ import annotations

from typing import Callable

import numpy as np

from autosim.pn.depletion_solver import solve_pn_depletion
from autosim.pn.poisson_solver import solve_pn_poisson
from autosim.pn.schemas import PnAgentDecision, PnNewtonProbe, PnSimInput, PnTrialResult


def solve_pn(
    sim_input: PnSimInput,
    on_probe: Callable[[PnNewtonProbe], PnAgentDecision | None] | None = None,
    trial_index: int = 0,
    psi_initial: np.ndarray | None = None,
    include_outputs: bool = True,
) -> PnTrialResult:
    """Route to appropriate physics model solver."""
    if sim_input.model_type == "depletion":
        return solve_pn_depletion(sim_input, on_probe=on_probe, trial_index=trial_index)
    if sim_input.model_type == "drift_diffusion":
        from autosim.pn.dd_solver import solve_dd_gummel

        result = solve_dd_gummel(
            sim_input, on_probe=on_probe, trial_index=trial_index, psi_initial=psi_initial
        )
        if sim_input.bias_scan.enabled:
            from autosim.pn.bias_sweep import run_bias_sweep

            _, sweep = run_bias_sweep(sim_input)
            result.sweep = sweep
        if include_outputs and sim_input.cv_scan.enabled:
            from autosim.pn.cv_sweep import run_cv_sweep

            cv = run_cv_sweep(sim_input)
            if result.sweep:
                result.sweep.points.extend(cv.points)
            else:
                from autosim.pn.schemas import PnSweepResult

                result.sweep = cv
        return result
    if sim_input.model_type == "transient_dd":
        from autosim.pn.transient_solver import solve_transient_dd

        return solve_transient_dd(sim_input, on_probe=on_probe, trial_index=trial_index)
    result = solve_pn_poisson(
        sim_input, on_probe=on_probe, trial_index=trial_index, psi_initial=psi_initial
    )
    if include_outputs and sim_input.cv_scan.enabled:
        from autosim.pn.cv_sweep import run_cv_sweep

        result.sweep = run_cv_sweep(sim_input)
    if sim_input.breakdown.enabled and result.profile:
        from autosim.pn.breakdown import breakdown_assessment
        from autosim.pn.postprocess import electric_field

        x = np.array([p.x for p in result.profile])
        psi = np.array([p.psi for p in result.profile])
        bd = breakdown_assessment(electric_field(psi, x), x, sim_input.breakdown)
        result.M_ionization = float(bd["M_ionization"])
        result.breakdown_risk = bool(bd["breakdown_risk"])
    return result
