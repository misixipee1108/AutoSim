"""Differential capacitance and C-V sweep."""

from __future__ import annotations

import numpy as np

from autosim.pn.schemas import CVScanSpec, PnSimInput, PnSweepPoint, PnSweepResult, PnTrialResult


def terminal_charge(rho: np.ndarray, x: np.ndarray) -> float:
    """Integrate space charge on n-side (x >= 0) for Q estimate (C/cm^2)."""
    if len(x) < 2:
        return 0.0
    mask = x >= 0
    if not np.any(mask):
        return 0.0
    xs = x[mask]
    rs = rho[mask]
    return float(np.trapezoid(rs, xs))


def differential_capacitance(
    sim_input: PnSimInput,
    base_result: PnTrialResult,
    delta_V: float | None = None,
) -> float | None:
    """C = -dQ/dV via symmetric finite difference on Vapp."""
    from autosim.pn.solve import solve_pn

    dV = delta_V or sim_input.cv_scan.delta_V
    if dV <= 0 or not base_result.profile:
        return None
    v0 = sim_input.Vapp
    base_inner = sim_input.model_copy(update={"cv_scan": CVScanSpec(enabled=False)})
    q0 = terminal_charge(
        np.array([p.rho for p in base_result.profile]),
        np.array([p.x for p in base_result.profile]),
    )
    up = solve_pn(base_inner.model_copy_with_params({"Vapp": v0 + dV}), include_outputs=False)
    dn = solve_pn(base_inner.model_copy_with_params({"Vapp": v0 - dV}), include_outputs=False)
    if not up.profile or not dn.profile:
        return None
    q_up = terminal_charge(np.array([p.rho for p in up.profile]), np.array([p.x for p in up.profile]))
    q_dn = terminal_charge(np.array([p.rho for p in dn.profile]), np.array([p.x for p in dn.profile]))
    return abs((q_up - q_dn) / (2.0 * dV))


def run_cv_sweep(base_input: PnSimInput, spec: CVScanSpec | None = None) -> PnSweepResult:
    from autosim.pn.solve import solve_pn

    cv = spec or base_input.cv_scan
    if cv.Vapp_step <= 0:
        raise ValueError("CV Vapp_step must be positive")
    points: list[PnSweepPoint] = []
    v = cv.Vapp_min
    while v <= cv.Vapp_max + cv.Vapp_step * 0.5:
        trial = base_input.model_copy_with_params({"Vapp": round(v, 10)})
        inner = trial.model_copy(update={"cv_scan": CVScanSpec(enabled=False)})
        result = solve_pn(inner, include_outputs=False)
        cj_diff = differential_capacitance(trial, result, cv.delta_V)
        points.append(
            PnSweepPoint(
                Vapp=v,
                Cj=result.Cj_estimate,
                Cj_diff=cj_diff,
                W=result.W_numeric,
                Emax=result.Emax_numeric,
                converged=result.converged,
                newton_iterations=result.newton_iterations,
            )
        )
        v += cv.Vapp_step
    return PnSweepResult(points=points, all_converged=all(p.converged for p in points))
