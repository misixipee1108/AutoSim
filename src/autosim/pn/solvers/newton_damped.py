"""Damped Newton with line search and scaled convergence criteria."""

from __future__ import annotations

from typing import Callable

import numpy as np
from autosim.pn.solvers.linear import solve_linear_system
from autosim.pn.solvers.checkpoint import load_checkpoint, save_checkpoint

from autosim.pn.convergence import (
    ConvergenceContext,
    ConvergenceSpec,
    check_convergence,
    interior_inf_norm,
    scale_metrics,
)
from autosim.pn.schemas import PnNewtonProbe


def _line_search(
    psi: np.ndarray,
    delta: np.ndarray,
    residual_fn: Callable,
    current_scaled_residual: float,
    alpha_init: float,
    conv_ctx: ConvergenceContext,
) -> tuple[np.ndarray, float]:
    alpha = alpha_init
    for _ in range(16):
        psi_trial = psi + alpha * delta
        F_trial, _, _ = residual_fn(psi_trial)
        trial_res = interior_inf_norm(F_trial)
        trial_scaled, _ = scale_metrics(conv_ctx, trial_res, 0.0)
        if trial_scaled < current_scaled_residual or alpha < 1e-5:
            return psi_trial, alpha
        alpha *= 0.5
    return psi + alpha * delta, alpha


def _risk_score(probe_data: dict, stall_count: int) -> float:
    score = 0.0
    if probe_data.get("exp_clamped"):
        score += 0.3
    if probe_data.get("stalled") or stall_count >= 10:
        score += 0.4
    cond = probe_data.get("jacobian_condition_estimate", 1.0)
    if cond > 1e10:
        score += 0.3
    return min(score, 1.0)


def _classify_failure(probe_data: dict, conv_result, conv_spec: ConvergenceSpec) -> str:
    if probe_data.get("is_nan"):
        return "exp_overflow"
    if probe_data.get("is_unphysical"):
        return "unphysical_carriers"
    if probe_data.get("exp_clamped"):
        return "exp_overflow"
    if probe_data.get("jacobian_condition_estimate", 0) > 1e12:
        return "ill_conditioned"
    if probe_data.get("stalled"):
        return "stalled"
    if conv_result.scaled_residual_norm > conv_spec.relative_tol * 100:
        return "bias_too_large"
    return "unknown"


def _recommend_action(failure_reason: str) -> str:
    mapping = {
        "exp_overflow": "increase_damping",
        "unphysical_carriers": "change_initial_guess",
        "ill_conditioned": "refine_mesh",
        "stalled": "increase_damping",
        "bias_too_large": "reduce_bias_step",
        "unknown": "switch_solver",
    }
    return mapping.get(failure_reason, "switch_solver")


def _interior_delta_norm(delta: np.ndarray) -> float:
    if len(delta) <= 2:
        return float(np.linalg.norm(delta, ord=np.inf))
    return float(np.linalg.norm(delta[1:-1], ord=np.inf))


def _estimate_jacobian_cond(J, n: int) -> float:
    if n > 400:
        return float(n)
    try:
        return float(np.linalg.cond(J.toarray()))
    except Exception:
        return float("inf")


class DampedNewtonSolver:
    name = "damped_newton"

    def solve(
        self,
        psi0: np.ndarray,
        residual_fn: Callable[[np.ndarray], tuple[np.ndarray, object, dict]],
        tol: float,
        max_iter: int,
        damping: float,
        on_probe: Callable[[PnNewtonProbe], object] | None,
        mesh_quality: float = 1.0,
        adaptive_damping: bool = False,
        conv_ctx: ConvergenceContext | None = None,
        conv_spec: ConvergenceSpec | None = None,
        linear_backend: str = "direct",
        checkpoint_dir: str | None = None,
    ) -> tuple[np.ndarray, list[PnNewtonProbe], bool, str]:
        if conv_ctx is None or conv_spec is None:
            raise ValueError("conv_ctx and conv_spec are required")

        psi = psi0.copy()
        if checkpoint_dir:
            restored = load_checkpoint(checkpoint_dir)
            if restored is not None and len(restored) == len(psi):
                psi = restored.copy()
        probes: list[PnNewtonProbe] = []
        prev_scaled_residual: float | None = None
        stall_count = 0
        current_damping = damping
        solver_warnings: list[str] = []

        for it in range(max_iter):
            F, J, extra = residual_fn(psi)
            residual_norm = interior_inf_norm(F)
            delta = solve_linear_system(J, -F, backend=linear_backend)
            delta_norm = _interior_delta_norm(delta)

            conv_result = check_convergence(conv_ctx, residual_norm, delta_norm, conv_spec)
            scaled_residual = conv_result.scaled_residual_norm
            scaled_delta = conv_result.scaled_delta_norm

            if prev_scaled_residual is not None and prev_scaled_residual > 0:
                rate = scaled_residual / prev_scaled_residual
            else:
                rate = 1.0

            try:
                cond = _estimate_jacobian_cond(J, len(psi))
            except Exception:
                cond = float("inf")

            if extra.get("exp_clamped") and "exp_clamped" not in solver_warnings:
                solver_warnings.append("exp_clamped")
            if cond > 1e12 and "ill_conditioned_jacobian" not in solver_warnings:
                solver_warnings.append("ill_conditioned_jacobian")

            probe_data = {
                **extra,
                "residual_norm": residual_norm,
                "residual_reduction_rate": rate,
                "delta_norm": delta_norm,
                "scaled_residual_norm": scaled_residual,
                "scaled_delta_norm": scaled_delta,
                "residual_scale": conv_ctx.residual_scale,
                "solution_scale": conv_ctx.solution_scale,
                "relative_tol": conv_spec.relative_tol,
                "convergence_criterion": conv_spec.criterion.value,
                "criterion_met": conv_result.criterion_met,
                "damping_factor": current_damping,
                "jacobian_condition_estimate": cond,
                "stalled": stall_count >= 15,
            }
            probe_data["convergence_risk_score"] = _risk_score(probe_data, stall_count)
            probe_data["mesh_quality_indicator"] = mesh_quality

            is_nan = extra.get("is_nan", False)
            is_unphysical = extra.get("is_unphysical", False)

            if is_nan:
                status = "failed_nan"
            elif is_unphysical:
                status = "failed_unphysical"
            elif stall_count >= 15:
                status = "stalled"
            elif conv_result.converged:
                status = "converged"
            else:
                status = "iterating"

            fail_reason = (
                _classify_failure(probe_data, conv_result, conv_spec)
                if status.startswith("failed") or status == "stalled"
                else ""
            )
            probe = PnNewtonProbe(
                iteration=it,
                residual_norm=residual_norm,
                residual_reduction_rate=rate,
                delta_norm=delta_norm,
                scaled_residual_norm=scaled_residual,
                scaled_delta_norm=scaled_delta,
                residual_scale=conv_ctx.residual_scale,
                solution_scale=conv_ctx.solution_scale,
                relative_tol=conv_spec.relative_tol,
                convergence_criterion=conv_spec.criterion.value,
                criterion_met=conv_result.criterion_met,
                damping_factor=current_damping,
                jacobian_condition_estimate=cond,
                max_psi=extra.get("max_psi", 0.0),
                min_psi=extra.get("min_psi", 0.0),
                max_electric_field=extra.get("max_electric_field", 0.0),
                max_carrier_density=extra.get("max_carrier_density", 0.0),
                min_n=extra.get("min_n", 0.0),
                min_p=extra.get("min_p", 0.0),
                charge_neutrality_error=extra.get("charge_neutrality_error", 0.0),
                is_nan=is_nan,
                is_unphysical=is_unphysical,
                exp_clamped=extra.get("exp_clamped", False),
                stalled=stall_count >= 15,
                convergence_status=status,
                failure_reason=fail_reason,
                recommended_numerical_action=_recommend_action(fail_reason) if fail_reason else "",
                convergence_risk_score=probe_data["convergence_risk_score"],
                mesh_quality_indicator=mesh_quality,
            )
            probes.append(probe)

            if checkpoint_dir and it % 5 == 0:
                save_checkpoint(checkpoint_dir, psi, iteration=it)

            if on_probe is not None:
                on_probe(probe)

            if is_nan or is_unphysical:
                return psi, probes, False, probe.failure_reason or "unphysical"
            if conv_result.converged:
                if checkpoint_dir:
                    save_checkpoint(checkpoint_dir, psi, iteration=it)
                return psi, probes, True, "converged"
            if stall_count >= 25 and scaled_residual > conv_spec.relative_tol * 200:
                return psi, probes, False, "Newton iteration stalled"

            if prev_scaled_residual is not None and scaled_residual >= prev_scaled_residual * 0.9995:
                stall_count += 1
            else:
                stall_count = 0

            if adaptive_damping and rate > 0.9:
                current_damping = max(current_damping * 0.8, 0.05)
            elif adaptive_damping and rate < 0.5:
                current_damping = min(current_damping * 1.1, 1.0)

            prev_scaled_residual = scaled_residual
            psi, current_damping = _line_search(
                psi, delta, residual_fn, scaled_residual, current_damping, conv_ctx
            )

        probe.convergence_status = "not_converged"
        probe.failure_reason = _classify_failure(probe_data, conv_result, conv_spec)
        probe.recommended_numerical_action = _recommend_action(probe.failure_reason)
        return psi, probes, False, "max_iter_reached"


class NewtonSolver(DampedNewtonSolver):
    name = "newton"


class NewtonLineSearchSolver(DampedNewtonSolver):
    name = "newton_line_search"

    def solve(self, psi0, residual_fn, tol, max_iter, damping, on_probe, mesh_quality=1.0, adaptive_damping=True, conv_ctx=None, conv_spec=None, linear_backend="direct", checkpoint_dir=None):
        return super().solve(
            psi0,
            residual_fn,
            tol,
            max_iter,
            damping,
            on_probe,
            mesh_quality,
            adaptive_damping=True,
            conv_ctx=conv_ctx,
            conv_spec=conv_spec,
            linear_backend=linear_backend,
            checkpoint_dir=checkpoint_dir,
        )
