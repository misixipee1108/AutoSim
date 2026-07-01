"""Drift-diffusion model entry (delegates to Gummel DD solver)."""

from __future__ import annotations

from typing import Callable

from autosim.pn.dd_solver import solve_dd_gummel
from autosim.pn.schemas import PnAgentDecision, PnNewtonProbe, PnSimInput, PnTrialResult


def solve_drift_diffusion(
    sim_input: PnSimInput,
    on_probe: Callable[[PnNewtonProbe], object] | None = None,
    trial_index: int = 0,
    psi_initial=None,
    max_gummel: int = 15,
    gummel_tol: float = 1e-3,
) -> PnTrialResult:
    return solve_dd_gummel(
        sim_input,
        on_probe=on_probe,
        trial_index=trial_index,
        psi_initial=psi_initial,
        max_gummel=max_gummel,
        gummel_tol=gummel_tol,
    )
