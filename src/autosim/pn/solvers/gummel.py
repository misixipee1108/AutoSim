"""Gummel iteration for Poisson + carrier continuity coupling."""

from __future__ import annotations

from typing import Callable

import numpy as np

from autosim.pn.schemas import PnNewtonProbe, PnSimInput


def run_gummel_loop(
    sim_input: PnSimInput,
    poisson_solve: Callable[..., tuple[np.ndarray, np.ndarray, np.ndarray, list[PnNewtonProbe], bool]],
    carrier_update: Callable[[np.ndarray, np.ndarray, np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray, float]],
    *,
    max_gummel: int = 20,
    gummel_tol: float = 1e-3,
    on_outer: Callable[[int, float, float], None] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[PnNewtonProbe], bool, int]:
    """Alternate Poisson solve and carrier update until carrier_update_norm < gummel_tol."""
    all_probes: list[PnNewtonProbe] = []
    n_guess: np.ndarray | None = None
    p_guess: np.ndarray | None = None
    psi = n = p = None
    converged = False
    for outer in range(max_gummel):
        psi, n, p, probes, poisson_ok = poisson_solve(n_guess, p_guess, outer)
        all_probes.extend(probes)
        n_new, p_new, update_norm = carrier_update(psi, n, p, outer)
        if on_outer:
            on_outer(outer, update_norm, probes[-1].max_electric_field if probes else 0.0)
        n_guess, p_guess = n_new, p_new
        n, p = n_new, p_new
        if update_norm < gummel_tol and poisson_ok:
            converged = True
            break
    return psi, n, p, all_probes, converged, outer + 1
