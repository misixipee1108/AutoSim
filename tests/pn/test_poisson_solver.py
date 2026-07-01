"""Tests for Poisson solver convergence."""

import pytest

from autosim.pn.poisson_solver import solve_pn_poisson
from autosim.pn.schemas import PnSimInput


@pytest.fixture
def benchmark_input():
    return PnSimInput(
        Na=1e18,
        Nd=1e16,
        Lp=2e-4,
        Ln=2e-4,
        Nx=200,
        Vapp=0.0,
        tol=5e-4,
        max_iter=200,
        damping=0.5,
    )


def test_poisson_converges(benchmark_input):
    result = solve_pn_poisson(benchmark_input)
    assert result.converged
    assert len(result.probes) > 0
    assert result.probes[-1].scaled_residual_norm < benchmark_input.tol
    assert result.probes[-1].scaled_delta_norm < benchmark_input.tol


def test_poisson_produces_profile(benchmark_input):
    result = solve_pn_poisson(benchmark_input)
    assert len(result.profile) == benchmark_input.Nx
    assert result.Vbi_numeric is not None
