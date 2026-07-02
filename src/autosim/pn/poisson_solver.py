"""1D nonlinear Poisson solver for PN junction (FDM + damped Newton)."""

from __future__ import annotations

from typing import Callable

import numpy as np
from scipy.sparse import diags

from autosim.materials.loader import load_material
from autosim.pn.analytical import contact_potentials, depletion_psi_profile
from autosim.pn.doping.factory import build_doping_array, bulk_doping_concentrations, get_doping_profile
from autosim.pn.schemas import BoundarySpec
from autosim.pn.mesh import build_mesh
from autosim.pn.postprocess import space_charge
from autosim.pn.schemas import (
    PnAgentAction,
    PnAgentDecision,
    PnNewtonProbe,
    PnSimInput,
    PnTrialResult,
)
from autosim.pn.convergence import (
    build_convergence_context,
    resolve_convergence_spec,
)
from autosim.pn.solvers.registry import get_solver
from autosim.pn.postprocess import finalize_result


def _build_doping_array(x: np.ndarray, doping) -> np.ndarray:
    return build_doping_array(x, doping)


def _residual_and_jacobian(
    psi: np.ndarray,
    x: np.ndarray,
    material,
    C: np.ndarray,
    psi_left: float,
    psi_right: float,
    exp_clamp: float,
    boundary: BoundarySpec | None = None,
    n_fixed: np.ndarray | None = None,
    p_fixed: np.ndarray | None = None,
) -> tuple[np.ndarray, object, dict]:
    N = len(psi)
    q = material.q
    eps = material.eps
    Vt = material.Vt
    ni = material.ni

    F = np.zeros(N)
    diag = np.zeros(N)
    lower = np.zeros(N - 1)
    upper = np.zeros(N - 1)

    u = np.clip(psi / Vt, -exp_clamp, exp_clamp)
    exp_clamped = bool(np.any(np.abs(psi / Vt) > exp_clamp))
    if n_fixed is not None and p_fixed is not None:
        n, p = n_fixed, p_fixed
    else:
        n = ni * np.exp(u)
        p = ni * np.exp(-u)

    bc = boundary or BoundarySpec()

    for i in range(N):
        if i == 0:
            if bc.left_type == "dirichlet":
                F[i] = psi[i] - psi_left
                diag[i] = 1.0
            else:
                dx = x[1] - x[0]
                F[i] = (psi[1] - psi[0]) / dx - bc.left_flux
                diag[i] = -1.0 / dx
                upper[0] = 1.0 / dx
            continue
        if i == N - 1:
            if bc.right_type == "dirichlet":
                F[i] = psi[i] - psi_right
                diag[i] = 1.0
            else:
                dx = x[N - 1] - x[N - 2]
                F[i] = (psi[N - 1] - psi[N - 2]) / dx - bc.right_flux
                diag[i] = 1.0 / dx
                lower[N - 2] = -1.0 / dx
            continue

        dx_m = x[i] - x[i - 1]
        dx_p = x[i + 1] - x[i]
        dpsi_m = (psi[i] - psi[i - 1]) / dx_m
        dpsi_p = (psi[i + 1] - psi[i]) / dx_p
        d2psi = 2.0 * (dpsi_p - dpsi_m) / (dx_m + dx_p)
        rho_sem = p[i] - n[i] + C[i]
        F[i] = d2psi + (q / eps) * rho_sem

        inv_sum = 2.0 / (dx_m + dx_p)
        if n_fixed is not None:
            coeff_psi = -inv_sum * (1.0 / dx_m + 1.0 / dx_p)
        else:
            coeff_psi = -inv_sum * (1.0 / dx_m + 1.0 / dx_p) - (q / (eps * Vt)) * (p[i] + n[i])
        diag[i] = coeff_psi
        lower[i - 1] = inv_sum / dx_m
        upper[i] = inv_sum / dx_p

    J = diags([lower, diag, upper], [-1, 0, 1], format="csr")

    rho = space_charge(n, p, C, q)
    E = np.zeros_like(psi)
    if len(psi) >= 3:
        E[1:-1] = -(psi[2:] - psi[:-2]) / (x[2:] - x[:-2])
    dx_arr = np.diff(x)
    charge_error = float(np.sum(rho[:-1] * dx_arr)) if len(dx_arr) else 0.0

    extra = {
        "max_psi": float(np.max(psi)),
        "min_psi": float(np.min(psi)),
        "max_electric_field": float(np.max(np.abs(E))),
        "max_carrier_density": float(max(np.max(n), np.max(p))),
        "min_n": float(np.min(n)),
        "min_p": float(np.min(p)),
        "charge_neutrality_error": charge_error,
        "is_nan": bool(np.any(np.isnan(psi)) or np.any(np.isnan(n)) or np.any(np.isnan(p))),
        "is_unphysical": bool(np.min(n) < 0 or np.min(p) < 0),
        "exp_clamped": exp_clamped,
    }
    return F, J, extra


def _mesh_quality(x: np.ndarray) -> float:
    dx = np.diff(x)
    if len(dx) == 0:
        return 1.0
    return float(np.min(dx) / np.max(dx))


def _handle_probe_decision(
    decision: PnAgentDecision,
    decisions: list[PnAgentDecision],
    damping: float,
) -> tuple[bool, float, str | None]:
    decisions.append(decision)
    if decision.action == PnAgentAction.EARLY_STOP:
        return True, damping, decision.reason
    if decision.action in (PnAgentAction.ADJUST_DAMPING, PnAgentAction.INCREASE_DAMPING):
        if decision.suggested_params and "damping" in decision.suggested_params:
            damping = float(decision.suggested_params["damping"])
        elif decision.action == PnAgentAction.INCREASE_DAMPING:
            damping = max(damping * 0.5, 0.05)
        return False, damping, None
    if decision.action in (PnAgentAction.CHANGE_INITIAL_GUESS, PnAgentAction.REFINE_MESH):
        return True, damping, "mesh_restart_requested"
    if decision.action == PnAgentAction.SWITCH_SOLVER:
        return True, damping, "solver_switch_requested"
    if decision.action == PnAgentAction.CONTINUE:
        return False, damping, None
    return False, damping, None


def solve_pn_poisson(
    sim_input: PnSimInput,
    on_probe: Callable[[PnNewtonProbe], PnAgentDecision | None] | None = None,
    trial_index: int = 0,
    psi_initial: np.ndarray | None = None,
    n_fixed: np.ndarray | None = None,
    p_fixed: np.ndarray | None = None,
) -> PnTrialResult:
    material = load_material(sim_input.material, sim_input.temperature_k)
    doping = get_doping_profile(sim_input)
    Na, Nd = bulk_doping_concentrations(sim_input)
    jr = sim_input.junction_refinement
    x, _ = build_mesh(
        sim_input.Lp,
        sim_input.Ln,
        sim_input.Nx,
        junction_refinement=jr.enabled,
        refinement_ratio=jr.ratio,
        width_frac=jr.width_frac,
    )
    C = _build_doping_array(x, doping)
    mq = _mesh_quality(x)

    psi_left, psi_right = contact_potentials(Na, Nd, material, sim_input.Vapp)
    psi = psi_initial if psi_initial is not None else depletion_psi_profile(
        x, Na, Nd, material, sim_input.Vapp
    )

    solver_spec = sim_input.solver
    method = solver_spec.method if sim_input.solver else "damped_newton"
    nl_solver = get_solver(method)

    probes: list[PnNewtonProbe] = []
    decisions: list[PnAgentDecision] = []
    damping = sim_input.damping
    early_stopped = False
    stop_reason = "completed"
    converged = False
    agent_stop = {"flag": False, "reason": ""}

    def residual_fn(psi_arr: np.ndarray):
        return _residual_and_jacobian(
            psi_arr, x, material, C, psi_left, psi_right,
            sim_input.exp_clamp, sim_input.boundary, n_fixed, p_fixed,
        )

    conv_spec = resolve_convergence_spec(
        tol=sim_input.tol,
        solver_spec_convergence=solver_spec.convergence if solver_spec else None,
    )
    psi_work = psi.copy()
    conv_ctx = build_convergence_context(
        psi_work,
        residual_fn,
        conv_spec,
        psi_left,
        psi_right,
    )

    def on_probe_cb(probe: PnNewtonProbe):
        if on_probe is not None:
            decision = on_probe(probe)
            if decision is not None:
                nonlocal damping, early_stopped, stop_reason
                should_break, damping, reason = _handle_probe_decision(
                    decision, decisions, damping
                )
                if should_break:
                    agent_stop["flag"] = True
                    agent_stop["reason"] = reason or decision.reason
                    early_stopped = reason not in (
                        "mesh_restart_requested", "solver_switch_requested"
                    )
                    stop_reason = agent_stop["reason"]

    psi_work, probes, converged, stop_reason = nl_solver.solve(
        psi_work,
        residual_fn,
        sim_input.tol,
        sim_input.max_iter,
        damping,
        on_probe_cb,
        mesh_quality=mq,
        adaptive_damping=solver_spec.adaptive_damping if solver_spec else False,
        conv_ctx=conv_ctx,
        conv_spec=conv_spec,
        linear_backend=solver_spec.linear_backend if solver_spec else "direct",
        checkpoint_dir=solver_spec.checkpoint_dir if solver_spec else None,
    )

    if stop_reason == "solver_switch_requested":
        alt = get_solver(
            "newton_line_search" if method != "newton_line_search" else "damped_newton"
        )
        psi_work, probes, converged, stop_reason = alt.solve(
            psi_work,
            residual_fn,
            sim_input.tol,
            sim_input.max_iter,
            damping,
            on_probe_cb,
            mq,
            adaptive_damping=True,
            conv_ctx=conv_ctx,
            conv_spec=conv_spec,
            linear_backend=solver_spec.linear_backend if solver_spec else "direct",
            checkpoint_dir=solver_spec.checkpoint_dir if solver_spec else None,
        )

    if agent_stop["flag"] and not converged:
        early_stopped = True
        stop_reason = agent_stop["reason"]

    result = finalize_result(
        sim_input, material, x, psi_work, C, probes, decisions,
        newton_iterations=len(probes),
        converged=converged,
        early_stopped=early_stopped and not converged,
        stop_reason=stop_reason,
        trial_index=trial_index,
        conv_spec=conv_spec,
        conv_ctx=conv_ctx,
    )
    result.model_type = "poisson"
    return result
