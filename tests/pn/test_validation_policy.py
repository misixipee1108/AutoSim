"""Validation policy and convergence status tests."""

from autosim.pn.poisson_solver import solve_pn_poisson
from autosim.pn.schemas import DopingSpec, PnSimInput, ValidationStatus
from autosim.pn.solve import solve_pn
from autosim.pn.validation import analytic_validation_eligible


def test_abrupt_analytic_validation_enabled():
    """Abrupt junction Poisson run performs analytic validation."""
    sim_input = PnSimInput(
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
    eligible, _ = analytic_validation_eligible(sim_input)
    assert eligible is True

    result = solve_pn_poisson(sim_input)
    assert result.converged
    assert result.validation is not None
    assert result.validation.status in (
        ValidationStatus.ANALYTIC_PASSED,
        ValidationStatus.ANALYTIC_FAILED,
    )
    assert result.validation.Vbi is not None
    assert result.validation.W_psi is not None


def test_linear_graded_validation_unavailable():
    """Graded doping has no analytic reference — status unavailable, numeric metrics kept."""
    sim_input = PnSimInput(
        Na=1e18,
        Nd=1e16,
        doping=DopingSpec(type="linear_graded", Na=1e18, Nd=1e16, params={"width": 1e-5}),
        Nx=150,
        tol=1e-3,
        max_iter=80,
    )
    eligible, reason = analytic_validation_eligible(sim_input)
    assert eligible is False
    assert "linear_graded" in reason

    result = solve_pn(sim_input)
    assert result.validation is not None
    assert result.validation.status == ValidationStatus.UNAVAILABLE
    assert "linear_graded" in result.validation.reason
    assert result.validation.Vbi is None
    assert result.validation.all_passed is False
    assert result.W_numeric is not None
    assert result.Emax_numeric is not None


def test_max_iter_not_converged():
    """Exhausting max_iter without meeting tol yields not converged."""
    sim_input = PnSimInput(
        Na=1e18,
        Nd=1e16,
        Nx=80,
        tol=1e-12,
        max_iter=3,
        damping=0.5,
    )
    result = solve_pn_poisson(sim_input)
    assert result.converged is False
    assert result.stop_reason == "max_iter_reached"
    assert result.probes
    assert result.probes[-1].scaled_residual_norm >= sim_input.tol or result.probes[-1].scaled_delta_norm >= sim_input.tol
    assert result.probes[-1].convergence_status == "not_converged"
