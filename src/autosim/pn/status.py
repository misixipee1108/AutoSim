"""Solver, validation, and run status derivation for PN trials."""

from __future__ import annotations

from autosim.pn.schemas import (
    PnNewtonProbe,
    PnValidationReport,
    SolverStatus,
    ValidationStatus,
)

_SOLVER_FAILURE_REASONS = frozenset({
    "exp_overflow",
    "unphysical_carriers",
    "ill_conditioned",
    "stalled",
    "bias_too_large",
    "unknown",
    "Newton iteration stalled",
})


def derive_solver_status(
    *,
    converged: bool,
    stop_reason: str,
    early_stopped: bool,
    probes: list[PnNewtonProbe],
    model_type: str = "poisson",
) -> SolverStatus:
    """Map Newton / solver outcome to solver_status only."""
    if model_type == "depletion" or stop_reason == "depletion_analytic":
        return SolverStatus.ANALYTIC_COMPLETE
    if model_type == "drift_diffusion" and stop_reason == "drift_diffusion_mvp":
        return SolverStatus.CONVERGED if converged else SolverStatus.NOT_CONVERGED

    if early_stopped and not converged:
        return SolverStatus.EARLY_STOPPED

    latest = probes[-1] if probes else None
    if latest is not None:
        if latest.is_nan or stop_reason in ("exp_overflow",) or latest.convergence_status == "failed_nan":
            return SolverStatus.FAILED_NAN
        if latest.is_unphysical or stop_reason == "unphysical_carriers":
            return SolverStatus.FAILED_UNPHYSICAL
        if latest.stalled or stop_reason == "Newton iteration stalled" or stop_reason == "stalled":
            return SolverStatus.STALLED

    if converged and stop_reason == "converged":
        return SolverStatus.CONVERGED
    if stop_reason == "max_iter_reached":
        return SolverStatus.MAX_ITER_REACHED
    if stop_reason in _SOLVER_FAILURE_REASONS:
        return SolverStatus.NOT_CONVERGED
    if not converged:
        return SolverStatus.NOT_CONVERGED
    return SolverStatus.CONVERGED


def derive_run_status(
    solver_status: SolverStatus,
    validation: PnValidationReport | None,
    *,
    early_stopped: bool = False,
) -> str:
    """Combine solver + validation into workflow run_status.

    Validation never marks Newton as converged; it only affects run_status.
    """
    if early_stopped or solver_status == SolverStatus.EARLY_STOPPED:
        return "early_stopped"

    validation_passed = (
        validation is not None
        and validation.status == ValidationStatus.ANALYTIC_PASSED
    )
    validation_failed = (
        validation is not None
        and validation.status == ValidationStatus.ANALYTIC_FAILED
    )
    validation_unavailable = (
        validation is None
        or validation.status in (ValidationStatus.UNAVAILABLE, ValidationStatus.NUMERICAL_ONLY)
    )

    hard_fail = solver_status in (
        SolverStatus.FAILED_NAN,
        SolverStatus.FAILED_UNPHYSICAL,
    )
    if hard_fail:
        return "failed"

    if solver_status == SolverStatus.STALLED:
        if validation_passed:
            return "completed_with_warning"
        return "failed"

    if solver_status == SolverStatus.CONVERGED or solver_status == SolverStatus.ANALYTIC_COMPLETE:
        if validation_failed:
            return "completed_with_warning"
        return "completed"

    if solver_status == SolverStatus.MAX_ITER_REACHED:
        if validation_passed or validation_unavailable:
            return "completed_with_warning"
        if validation_failed:
            return "failed"
        return "failed"

    if solver_status == SolverStatus.NOT_CONVERGED:
        if validation_passed:
            return "completed_with_warning"
        if validation_unavailable:
            return "completed_with_warning"
        return "failed"

    return "failed"


def run_status_to_api(status: str) -> str:
    """Map internal run_status string to API RunStatus value."""
    mapping = {
        "completed": "completed",
        "completed_with_warning": "completed_with_warning",
        "failed": "failed",
        "early_stopped": "early_stopped",
    }
    return mapping.get(status, "failed")


def validation_status_for_api(validation: PnValidationReport | None) -> str | None:
    if validation is None:
        return None
    if validation.status == ValidationStatus.ANALYTIC_PASSED:
        return "passed"
    if validation.status == ValidationStatus.ANALYTIC_FAILED:
        return "failed"
    if validation.status == ValidationStatus.NUMERICAL_ONLY:
        return "numerical_only"
    return validation.status.value
