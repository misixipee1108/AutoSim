"""COMSOL-style scaled convergence criteria for PN Newton solvers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Literal

import numpy as np
from pydantic import BaseModel, Field


class ConvergenceCriterion(str, Enum):
    RESIDUAL = "residual"
    SOLUTION = "solution"
    EITHER = "either"
    BOTH = "both"


class ConvergenceSpec(BaseModel):
    criterion: ConvergenceCriterion = ConvergenceCriterion.BOTH
    relative_tol: float = 1e-4
    absolute_tol: float | None = None
    scaling_mode: Literal["auto", "initial", "manual"] = "auto"
    residual_scale: float | None = None
    solution_scale: float | None = None
    scale_floor: float = 1e-12


@dataclass(frozen=True)
class ConvergenceContext:
    residual_scale: float
    solution_scale: float


@dataclass(frozen=True)
class ConvergenceResult:
    converged: bool
    criterion_met: str  # residual | solution | both | none
    scaled_residual_norm: float
    scaled_delta_norm: float
    residual_ok: bool
    solution_ok: bool


def interior_inf_norm(arr: np.ndarray) -> float:
    if len(arr) <= 2:
        return float(np.linalg.norm(arr, ord=np.inf))
    return float(np.linalg.norm(arr[1:-1], ord=np.inf))


def resolve_convergence_spec(
    *,
    tol: float,
    solver_spec_convergence: ConvergenceSpec | None = None,
) -> ConvergenceSpec:
    """Build effective convergence spec; flat ``tol`` maps to ``relative_tol``."""
    base = solver_spec_convergence or ConvergenceSpec()
    return base.model_copy(update={"relative_tol": tol})


def build_convergence_context(
    psi0: np.ndarray,
    residual_fn: Callable[[np.ndarray], tuple[np.ndarray, object, dict]],
    spec: ConvergenceSpec,
    psi_left: float,
    psi_right: float,
) -> ConvergenceContext:
    """Fix reference scales at Newton start (do not update during iteration)."""
    if spec.scaling_mode == "manual":
        r_scale = spec.residual_scale if spec.residual_scale is not None else spec.scale_floor
        s_scale = spec.solution_scale if spec.solution_scale is not None else spec.scale_floor
        return ConvergenceContext(
            residual_scale=max(float(r_scale), spec.scale_floor),
            solution_scale=max(float(s_scale), spec.scale_floor),
        )

    F0, _, _ = residual_fn(psi0)
    r_scale = max(interior_inf_norm(F0), spec.scale_floor)

    if len(psi0) > 2:
        psi_interior = float(np.linalg.norm(psi0[1:-1], ord=np.inf))
    else:
        psi_interior = float(np.linalg.norm(psi0, ord=np.inf))
    s_scale = max(psi_interior, abs(psi_left), abs(psi_right), spec.scale_floor)

    return ConvergenceContext(residual_scale=r_scale, solution_scale=s_scale)


def scale_metrics(
    ctx: ConvergenceContext,
    raw_residual: float,
    raw_delta: float,
) -> tuple[float, float]:
    return raw_residual / ctx.residual_scale, raw_delta / ctx.solution_scale


def check_convergence(
    ctx: ConvergenceContext,
    raw_residual: float,
    raw_delta: float,
    spec: ConvergenceSpec,
) -> ConvergenceResult:
    scaled_r, scaled_d = scale_metrics(ctx, raw_residual, raw_delta)

    residual_ok = scaled_r < spec.relative_tol
    solution_ok = scaled_d < spec.relative_tol
    if spec.absolute_tol is not None:
        if raw_residual < spec.absolute_tol:
            residual_ok = True
        if raw_delta < spec.absolute_tol:
            solution_ok = True

    criterion = spec.criterion
    if criterion == ConvergenceCriterion.RESIDUAL:
        converged = residual_ok
        met = "residual" if residual_ok else "none"
    elif criterion == ConvergenceCriterion.SOLUTION:
        converged = solution_ok
        met = "solution" if solution_ok else "none"
    elif criterion == ConvergenceCriterion.EITHER:
        converged = residual_ok or solution_ok
        if residual_ok and solution_ok:
            met = "both"
        elif residual_ok:
            met = "residual"
        elif solution_ok:
            met = "solution"
        else:
            met = "none"
    else:  # BOTH
        converged = residual_ok and solution_ok
        if converged:
            met = "both"
        elif residual_ok:
            met = "residual"
        elif solution_ok:
            met = "solution"
        else:
            met = "none"

    return ConvergenceResult(
        converged=converged,
        criterion_met=met,
        scaled_residual_norm=scaled_r,
        scaled_delta_norm=scaled_d,
        residual_ok=residual_ok,
        solution_ok=solution_ok,
    )


def build_convergence_summary(
    spec: ConvergenceSpec,
    ctx: ConvergenceContext,
    probes: list,
    solver_warnings: list[str] | None = None,
):
    from autosim.pn.schemas import ConvergenceSummary, PnNewtonProbe

    latest: PnNewtonProbe | None = probes[-1] if probes else None
    return ConvergenceSummary(
        criterion=spec.criterion.value,
        relative_tol=spec.relative_tol,
        absolute_tol=spec.absolute_tol,
        residual_scale=ctx.residual_scale,
        solution_scale=ctx.solution_scale,
        final_residual_norm=latest.residual_norm if latest else 0.0,
        final_scaled_residual_norm=latest.scaled_residual_norm if latest else 0.0,
        final_delta_norm=latest.delta_norm if latest else 0.0,
        final_scaled_delta_norm=latest.scaled_delta_norm if latest else 0.0,
        criterion_met=latest.criterion_met if latest else "none",
        solver_warnings=solver_warnings or [],
    )
