"""Three-layer status: solver_status, validation_status, run_status."""

from autosim.api.adapters.pn import PnAdapter
from autosim.pn.poisson_solver import solve_pn_poisson
from autosim.pn.schemas import (
    DopingSpec,
    PnSimInput,
    PnValidationReport,
    SolverStatus,
    ValidationStatus,
)
from autosim.pn.status import derive_run_status, derive_solver_status
from autosim.pn.solve import solve_pn


def test_solver_status_converged():
    inp = PnSimInput(Na=1e18, Nd=1e16, Nx=200, tol=5e-4, max_iter=200, damping=0.5)
    result = solve_pn_poisson(inp)
    assert result.solver_status == SolverStatus.CONVERGED
    assert result.run_status == "completed"


def test_solver_max_iter_with_validation_passed_is_warning():
    inp = PnSimInput(
        Na=1e18,
        Nd=1e16,
        Nx=200,
        tol=1e-12,
        max_iter=5,
        damping=0.5,
    )
    result = solve_pn_poisson(inp)
    assert result.solver_status == SolverStatus.MAX_ITER_REACHED
    assert result.converged is False
    assert result.validation is not None
    assert result.validation.status == ValidationStatus.ANALYTIC_PASSED
    assert result.run_status == "completed_with_warning"

    adapter = PnAdapter()
    unified = adapter.normalize_result("test-run", result)
    assert unified.status.value == "completed_with_warning"
    assert unified.solver_status == "max_iter_reached"
    assert unified.validation_status == "passed"
    assert unified.run_status == "completed_with_warning"
    assert unified.error is None


def test_graded_doping_validation_unavailable_run_warning_on_max_iter():
    inp = PnSimInput(
        Na=1e18,
        Nd=1e16,
        doping=DopingSpec(type="linear_graded", Na=1e18, Nd=1e16, params={"width": 1e-5}),
        Nx=120,
        tol=1e-12,
        max_iter=3,
    )
    result = solve_pn(inp)
    assert result.validation.status == ValidationStatus.UNAVAILABLE
    assert result.solver_status == SolverStatus.MAX_ITER_REACHED
    assert result.run_status == "completed_with_warning"
    assert "linear_graded" in result.validation.reason


def test_analytic_failed_with_max_iter_is_failed():
    report = PnValidationReport(status=ValidationStatus.ANALYTIC_FAILED, reason="")
    status = derive_run_status(SolverStatus.MAX_ITER_REACHED, report)
    assert status == "failed"


def test_derive_solver_status_from_stop_reason():
    assert derive_solver_status(
        converged=False,
        stop_reason="max_iter_reached",
        early_stopped=False,
        probes=[],
    ) == SolverStatus.MAX_ITER_REACHED
