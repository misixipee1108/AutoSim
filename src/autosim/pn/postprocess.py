"""Post-processing of converged Poisson solution."""

from __future__ import annotations

import math

import numpy as np

from autosim.pn.analytical import contact_potentials, depletion_width
from autosim.pn.doping.factory import bulk_doping_concentrations
from autosim.pn.materials import MaterialSpec
from autosim.pn.schemas import (
    PnSimInput,
    PnTrialResult,
    ProfilePoint,
)
from autosim.pn.validation import (
    analytic_validation_eligible,
    build_validation_report,
    skipped_validation_report,
)
from autosim.pn.convergence import ConvergenceContext, ConvergenceSpec, build_convergence_summary
from autosim.pn.status import derive_run_status, derive_solver_status


def _collect_solver_warnings(probes: list) -> list[str]:
    warnings: list[str] = []
    if not probes:
        return warnings
    latest = probes[-1]
    if getattr(latest, "exp_clamped", False) and "exp_clamped" not in warnings:
        warnings.append("exp_clamped")
    if getattr(latest, "jacobian_condition_estimate", 0) > 1e12:
        warnings.append("ill_conditioned_jacobian")
    return warnings


def carrier_densities(
    psi: np.ndarray,
    material: MaterialSpec,
    exp_clamp: float,
) -> tuple[np.ndarray, np.ndarray, bool]:
    """Boltzmann carriers with clamping."""
    Vt = material.Vt
    ni = material.ni
    u = np.clip(psi / Vt, -exp_clamp, exp_clamp)
    clamped = np.any(np.abs(psi / Vt) > exp_clamp)
    n = ni * np.exp(u)
    p = ni * np.exp(-u)
    return n, p, bool(clamped)


def space_charge(
    n: np.ndarray,
    p: np.ndarray,
    C: np.ndarray,
    q: float,
) -> np.ndarray:
    return q * (p - n + C)


def electric_field(psi: np.ndarray, x: np.ndarray) -> np.ndarray:
    E = np.zeros_like(psi)
    if len(psi) < 2:
        return E
    dx = np.diff(x)
    E[1:-1] = -(psi[2:] - psi[:-2]) / (x[2:] - x[:-2])
    E[0] = -(psi[1] - psi[0]) / dx[0]
    E[-1] = -(psi[-1] - psi[-2]) / dx[-1]
    return E


def estimate_depletion_width(
    x: np.ndarray,
    psi: np.ndarray,
    psi_p: float,
    psi_n: float,
    Vbi: float,
    threshold_frac: float = 0.05,
) -> float:
    """Estimate W from potential deviation from bulk contact values."""
    if Vbi <= 0:
        return 0.0
    threshold = threshold_frac * abs(Vbi)
    left_edge = x[0]
    for i, xi in enumerate(x):
        if xi <= 0 and psi[i] > psi_p + threshold:
            left_edge = xi
            break
    right_edge = x[-1]
    for i in range(len(x) - 1, -1, -1):
        if x[i] >= 0 and psi[i] < psi_n - threshold:
            right_edge = x[i]
            break
    return float(right_edge - left_edge)


def estimate_depletion_width_rho(
    x: np.ndarray,
    rho: np.ndarray,
    Na: float,
    Nd: float,
    q: float,
    threshold_frac: float = 0.05,
) -> float:
    """Estimate W from space charge density exceeding a peak-scaled threshold."""
    rho_abs = np.abs(rho)
    peak = float(np.max(rho_abs))
    if peak <= 0:
        return 0.0
    threshold = threshold_frac * peak
    charged = rho_abs > threshold
    if not np.any(charged):
        return 0.0
    # Expand to neighbors while local charge remains significant
    indices = np.where(charged)[0]
    i0, i1 = int(indices[0]), int(indices[-1])
    while i0 > 0 and rho_abs[i0 - 1] > threshold * 0.1:
        i0 -= 1
    while i1 < len(x) - 1 and rho_abs[i1 + 1] > threshold * 0.1:
        i1 += 1
    return float(x[i1] - x[i0])

def build_profile(
    x: np.ndarray,
    psi: np.ndarray,
    material: MaterialSpec,
    C: np.ndarray,
    exp_clamp: float,
) -> list[ProfilePoint]:
    n, p, _ = carrier_densities(psi, material, exp_clamp)
    rho = space_charge(n, p, C, material.q)
    E = electric_field(psi, x)
    return [
        ProfilePoint(x=float(x[i]), psi=float(psi[i]), E=float(E[i]),
                     n=float(n[i]), p=float(p[i]), rho=float(rho[i]))
        for i in range(len(x))
    ]


def finalize_result(
    sim_input: PnSimInput,
    material: MaterialSpec,
    x: np.ndarray,
    psi: np.ndarray,
    C: np.ndarray,
    probes: list,
    decisions: list,
    newton_iterations: int,
    converged: bool,
    early_stopped: bool,
    stop_reason: str,
    trial_index: int = 0,
    conv_spec: ConvergenceSpec | None = None,
    conv_ctx: ConvergenceContext | None = None,
) -> PnTrialResult:
    n, p, _ = carrier_densities(psi, material, sim_input.exp_clamp)
    rho = space_charge(n, p, C, material.q)
    E = electric_field(psi, x)

    psi_p, psi_n = contact_potentials(
        *bulk_doping_concentrations(sim_input), material, sim_input.Vapp
    )
    Na, Nd = bulk_doping_concentrations(sim_input)
    Vbi_numeric = float(psi_n - psi_p)
    W_psi = estimate_depletion_width(
        x, psi, psi_p, psi_n, Vbi_numeric, sim_input.psi_threshold_frac
    )
    W_rho = estimate_depletion_width_rho(
        x, rho, Na, Nd, material.q, sim_input.rho_threshold_frac
    )
    W_numeric = W_rho if W_rho > 0 else W_psi
    Emax_numeric = float(np.max(np.abs(E)))

    analytic = depletion_width(
        Na, Nd, material, sim_input.Vapp
    )
    eps = material.eps
    Cj = eps / W_rho if W_rho > 0 else (eps / W_psi if W_psi > 0 else None)
    cj_method = "W_rho" if W_rho > 0 else "W_psi"

    eligible, skip_reason = analytic_validation_eligible(sim_input)
    if eligible:
        validation = build_validation_report(
            Vbi_numeric, W_numeric, W_psi, W_rho, Emax_numeric, analytic
        )
    else:
        validation = skipped_validation_report(sim_input, skip_reason)

    profile = build_profile(x, psi, material, C, sim_input.exp_clamp)

    solver_status = derive_solver_status(
        converged=converged,
        stop_reason=stop_reason,
        early_stopped=early_stopped,
        probes=probes,
        model_type=sim_input.model_type,
    )
    run_status = derive_run_status(
        solver_status,
        validation,
        early_stopped=early_stopped,
    )

    convergence_summary = None
    if conv_spec is not None and conv_ctx is not None:
        convergence_summary = build_convergence_summary(
            conv_spec,
            conv_ctx,
            probes,
            _collect_solver_warnings(probes),
        )

    return PnTrialResult(
        trial_index=trial_index,
        input=sim_input,
        profile=profile,
        probes=probes,
        decisions=decisions,
        Vbi_numeric=Vbi_numeric,
        W_numeric=W_numeric,
        W_psi_numeric=W_psi,
        W_rho_numeric=W_rho,
        Emax_numeric=Emax_numeric,
        Cj_estimate=Cj,
        Cj_method=cj_method,
        newton_iterations=newton_iterations,
        converged=converged,
        early_stopped=early_stopped,
        stop_reason=stop_reason,
        solver_status=solver_status,
        run_status=run_status,
        validation=validation,
        convergence_summary=convergence_summary,
        model_type=sim_input.model_type,
    )
