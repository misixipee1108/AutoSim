"""Numerical vs analytical validation tests."""

import pytest

from autosim.pn.poisson_solver import solve_pn_poisson
from autosim.pn.schemas import PnSimInput, ValidationStatus


def test_equilibrium_validation_benchmark():
    sim_input = PnSimInput(
        Na=1e18,
        Nd=1e16,
        Lp=2e-4,
        Ln=2e-4,
        Nx=400,
        Vapp=0.0,
        tol=5e-4,
        max_iter=300,
        damping=0.5,
    )
    result = solve_pn_poisson(sim_input)
    assert result.converged
    assert result.validation is not None
    assert result.validation.status == ValidationStatus.ANALYTIC_PASSED
    assert result.validation.Vbi is not None
    assert result.validation.Vbi.passed, (
        f"Vbi rel_error={result.validation.Vbi.rel_error:.4f}"
    )
    assert result.validation.W is not None
    assert result.validation.W_psi is not None
    assert result.validation.W_rho is not None
    assert result.validation.W_psi.passed or result.validation.W_rho.passed, (
        f"W_psi rel_error={result.validation.W_psi.rel_error:.4f}, "
        f"W_rho rel_error={result.validation.W_rho.rel_error:.4f}"
    )
