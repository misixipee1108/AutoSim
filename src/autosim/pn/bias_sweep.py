"""Bias voltage sweep for 1D PN junction."""

from __future__ import annotations

import numpy as np

from autosim.pn.schemas import BiasScanSpec, PnSimInput, PnSweepPoint, PnSweepResult, PnTrialResult


def build_vapp_list(spec: BiasScanSpec, base_vapp: float = 0.0) -> list[float]:
    """Build list of applied bias values from sweep spec."""
    if spec.Vapp_list:
        return list(spec.Vapp_list)
    if not spec.enabled:
        return [base_vapp]
    if spec.Vapp_step <= 0:
        raise ValueError("Vapp_step must be positive")
    points: list[float] = []
    v = spec.Vapp_min
    while v <= spec.Vapp_max + spec.Vapp_step * 0.5:
        points.append(round(v, 10))
        v += spec.Vapp_step
    if not points:
        points = [base_vapp]
    return points


def run_bias_sweep(
    base_input: PnSimInput,
    spec: BiasScanSpec | None = None,
) -> tuple[list[PnTrialResult], PnSweepResult]:
    """Run solve at each bias point with optional warm-start continuation."""
    from autosim.pn.breakdown import breakdown_assessment
    from autosim.pn.postprocess import electric_field
    from autosim.pn.solve import solve_pn

    sweep_spec = spec or base_input.bias_scan
    vapp_values = build_vapp_list(sweep_spec, base_input.Vapp)
    if sweep_spec.continuation and not sweep_spec.Vapp_list:
        vapp_values = sorted(vapp_values)

    trial_results: list[PnTrialResult] = []
    sweep_points: list[PnSweepPoint] = []
    psi_warm: np.ndarray | None = None
    current_step = sweep_spec.Vapp_step if sweep_spec.Vapp_step > 0 else 0.1
    adaptive_step = current_step

    idx = 0
    while idx < len(vapp_values):
        vapp = vapp_values[idx]
        trial_input = base_input.model_copy_with_params({"Vapp": vapp})
        try:
            result = solve_pn(
                trial_input,
                trial_index=idx,
                psi_initial=psi_warm if sweep_spec.warm_start and psi_warm is not None else None,
            )
        except Exception:
            if sweep_spec.continuation and adaptive_step > 0.005:
                adaptive_step *= 0.5
                half_vapp = vapp - np.sign(vapp - (vapp_values[idx - 1] if idx > 0 else 0)) * adaptive_step
                trial_input = base_input.model_copy_with_params({"Vapp": half_vapp})
                result = solve_pn(trial_input, trial_index=idx, psi_initial=psi_warm)
                vapp = half_vapp
            else:
                raise

        if result.converged and result.profile and sweep_spec.warm_start:
            psi_warm = np.array([p.psi for p in result.profile])

        M = result.M_ionization
        bd_risk = result.breakdown_risk
        if base_input.breakdown.enabled and result.profile and M is None:
            x = np.array([p.x for p in result.profile])
            psi = np.array([p.psi for p in result.profile])
            bd = breakdown_assessment(electric_field(psi, x), x, base_input.breakdown, result.J_terminal)
            M = float(bd["M_ionization"])
            bd_risk = bool(bd["breakdown_risk"])

        trial_results.append(result)
        sweep_points.append(
            PnSweepPoint(
                Vapp=vapp,
                W=result.W_numeric,
                W_psi=result.W_psi_numeric,
                W_rho=result.W_rho_numeric,
                Cj=result.Cj_estimate,
                Emax=result.Emax_numeric,
                Vbi=result.Vbi_numeric,
                J=result.J_terminal,
                M=M,
                breakdown_risk=bool(bd_risk),
                converged=result.converged,
                newton_iterations=result.newton_iterations,
            )
        )
        idx += 1
        if result.converged and vapp > 0 and sweep_spec.continuation:
            adaptive_step = min(adaptive_step * 1.1, current_step)

    sweep = PnSweepResult(
        points=sweep_points,
        all_converged=all(p.converged for p in sweep_points),
    )
    if trial_results:
        trial_results[-1].sweep = sweep
    return trial_results, sweep
