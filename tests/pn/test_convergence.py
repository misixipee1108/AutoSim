"""Scaled convergence criteria tests."""

import numpy as np

from autosim.pn.convergence import (
    ConvergenceContext,
    ConvergenceCriterion,
    ConvergenceSpec,
    build_convergence_context,
    check_convergence,
    interior_inf_norm,
    resolve_convergence_spec,
    scale_metrics,
)
from autosim.pn.poisson_solver import solve_pn_poisson
from autosim.pn.schemas import PnSimInput, SolverSpec


def test_interior_inf_norm_excludes_boundaries():
    F = np.array([1.0, 100.0, 50.0, 2.0])
    assert interior_inf_norm(F) == 100.0


def test_resolve_convergence_spec_maps_tol():
    spec = resolve_convergence_spec(tol=5e-4, solver_spec_convergence=ConvergenceSpec())
    assert spec.relative_tol == 5e-4
    assert spec.criterion == ConvergenceCriterion.BOTH


def test_check_convergence_both_requires_residual_and_solution():
    ctx = ConvergenceContext(residual_scale=1e6, solution_scale=1.0)
    spec = ConvergenceSpec(criterion=ConvergenceCriterion.BOTH, relative_tol=1e-4)
    ok = check_convergence(ctx, raw_residual=10.0, raw_delta=1e-5, spec=spec)
    assert ok.residual_ok is True
    assert ok.solution_ok is True
    assert ok.converged is True
    assert ok.criterion_met == "both"

    partial = check_convergence(ctx, raw_residual=10.0, raw_delta=0.1, spec=spec)
    assert partial.residual_ok is True
    assert partial.solution_ok is False
    assert partial.converged is False
    assert partial.criterion_met == "residual"


def test_check_convergence_either():
    ctx = ConvergenceContext(residual_scale=1.0, solution_scale=1.0)
    spec = ConvergenceSpec(criterion=ConvergenceCriterion.EITHER, relative_tol=1e-3)
    result = check_convergence(ctx, raw_residual=1e-4, raw_delta=1.0, spec=spec)
    assert result.converged is True
    assert result.criterion_met == "residual"


def test_manual_scaling_mode():
    inp = PnSimInput(
        Na=1e18,
        Nd=1e16,
        Nx=100,
        tol=1e-4,
        max_iter=200,
        damping=0.5,
        solver=SolverSpec(
            convergence=ConvergenceSpec(
                scaling_mode="manual",
                residual_scale=1e8,
                solution_scale=0.5,
            )
        ),
    )

    def dummy_residual(psi):
        F = np.ones_like(psi) * 1e6
        return F, None, {}

    ctx = build_convergence_context(
        np.zeros(10),
        dummy_residual,
        resolve_convergence_spec(tol=inp.tol, solver_spec_convergence=inp.solver.convergence),
        0.0,
        0.7,
    )
    assert ctx.residual_scale == 1e8
    assert ctx.solution_scale == 0.5


def test_absolute_tol_floor():
    ctx = ConvergenceContext(residual_scale=1e12, solution_scale=1e12)
    spec = ConvergenceSpec(
        criterion=ConvergenceCriterion.BOTH,
        relative_tol=1e-12,
        absolute_tol=1e-2,
    )
    result = check_convergence(ctx, raw_residual=5e-3, raw_delta=5e-3, spec=spec)
    assert result.converged is True


def test_poisson_scaled_convergence_metrics():
    inp = PnSimInput(Na=1e18, Nd=1e16, Nx=200, tol=5e-4, max_iter=200, damping=0.5)
    result = solve_pn_poisson(inp)
    assert result.converged
    assert result.convergence_summary is not None
    last = result.probes[-1]
    assert last.scaled_residual_norm < inp.tol
    assert last.scaled_delta_norm < inp.tol
    assert result.convergence_summary.criterion_met == "both"


def test_scale_metrics():
    ctx = ConvergenceContext(residual_scale=2.0, solution_scale=4.0)
    sr, sd = scale_metrics(ctx, 10.0, 8.0)
    assert sr == 5.0
    assert sd == 2.0
