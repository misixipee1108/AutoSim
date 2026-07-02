"""Analytic validation eligibility and report building."""

from __future__ import annotations

from autosim.pn.analytical import DepletionAnalytic, shockley_current, shockley_saturation_current
from autosim.materials.loader import load_material
from autosim.pn.schemas import (
    PnSimInput,
    PnValidationReport,
    ValidationMetric,
    ValidationStatus,
)

_NON_ABRUPT_DOPING = frozenset({
    "linear_graded",
    "gaussian",
    "piecewise",
    "erfc",
    "custom",
    "table",
})


def analytic_validation_eligible(sim_input: PnSimInput) -> tuple[bool, str]:
    """Return whether abrupt depletion analytic reference applies."""
    if sim_input.model_type == "drift_diffusion":
        return False, "no analytic reference for model_type=drift_diffusion (MVP)"

    doping_type = sim_input.doping.type if sim_input.doping else "abrupt"
    if doping_type in _NON_ABRUPT_DOPING:
        return False, f"no analytic reference for doping.type={doping_type}"

    if sim_input.model_type not in ("poisson", "depletion"):
        return False, f"no analytic reference for model_type={sim_input.model_type}"

    return True, ""


def validation_skip_kind(sim_input: PnSimInput, skip_reason: str) -> ValidationStatus:
    """Classify skipped validation as numerical_only vs unavailable."""
    doping_type = sim_input.doping.type if sim_input.doping else "abrupt"
    if doping_type in _NON_ABRUPT_DOPING:
        return ValidationStatus.NUMERICAL_ONLY
    return ValidationStatus.UNAVAILABLE


def _metric(num: float, ana: float, tol: float) -> ValidationMetric:
    if ana == 0:
        rel = abs(num - ana)
        passed = rel < tol
    else:
        rel = abs(num - ana) / abs(ana)
        passed = rel < tol
    return ValidationMetric(numeric=num, analytic=ana, rel_error=rel, passed=passed)


def shockley_validation_eligible(sim_input: PnSimInput) -> tuple[bool, str]:
    """Return whether Shockley diode analytic reference applies."""
    if sim_input.model_type != "drift_diffusion":
        return False, "Shockley validation requires model_type=drift_diffusion"
    doping_type = sim_input.doping.type if sim_input.doping else "abrupt"
    if doping_type != "abrupt":
        return False, f"Shockley validation requires abrupt doping, got {doping_type}"
    if sim_input.Vapp <= 0:
        return False, "Shockley validation requires forward bias Vapp > 0"
    return True, ""


def build_shockley_validation_report(
    J_numeric: float,
    sim_input: PnSimInput,
    *,
    ideality: float = 1.0,
    j_tol: float = 2.0,
) -> PnValidationReport:
    """Compare terminal current against Shockley diode equation."""
    material = load_material(sim_input.material, sim_input.temperature_k)
    Na = sim_input.doping.Na if sim_input.doping and sim_input.doping.Na else sim_input.Na
    Nd = sim_input.doping.Nd if sim_input.doping and sim_input.doping.Nd else sim_input.Nd
    Js = shockley_saturation_current(Na, Nd, material, sim_input.Lp, sim_input.Ln)
    J_ana = shockley_current(sim_input.Vapp, Js, material, ideality)
    J_m = _metric(J_numeric, J_ana, j_tol)
    status = ValidationStatus.ANALYTIC_PASSED if J_m.passed else ValidationStatus.ANALYTIC_FAILED
    return PnValidationReport(
        status=status,
        reason="shockley_diode",
        all_passed=J_m.passed,
    )


def build_validation_report(
    Vbi_numeric: float,
    W_numeric: float,
    W_psi: float,
    W_rho: float,
    Emax_numeric: float,
    analytic: DepletionAnalytic,
    vbi_tol: float = 0.02,
    w_tol: float = 0.40,
    emax_tol: float = 0.15,
) -> PnValidationReport:
    """Compare numeric metrics against abrupt depletion analytic reference."""
    Vbi_m = _metric(Vbi_numeric, analytic.Vbi, vbi_tol)
    W_m = _metric(W_numeric, analytic.W, w_tol)
    W_psi_m = _metric(W_psi, analytic.W, w_tol)
    W_rho_m = _metric(W_rho, analytic.W, w_tol)
    Emax_m = _metric(Emax_numeric, analytic.Emax, emax_tol)
    all_passed = Vbi_m.passed and W_psi_m.passed and Emax_m.passed
    status = ValidationStatus.ANALYTIC_PASSED if all_passed else ValidationStatus.ANALYTIC_FAILED
    return PnValidationReport(
        status=status,
        reason="",
        Vbi=Vbi_m,
        W=W_m,
        W_psi=W_psi_m,
        W_rho=W_rho_m,
        Emax=Emax_m,
        all_passed=all_passed,
    )


def unavailable_validation_report(reason: str) -> PnValidationReport:
    """Validation skipped — numeric metrics only, no pass/fail against analytic."""
    return PnValidationReport(
        status=ValidationStatus.UNAVAILABLE,
        reason=reason,
        all_passed=False,
    )


def numerical_only_validation_report(reason: str) -> PnValidationReport:
    """Non-abrupt doping — compare against frozen reference metrics, not abrupt analytic."""
    return PnValidationReport(
        status=ValidationStatus.NUMERICAL_ONLY,
        reason=reason,
        all_passed=False,
    )


def skipped_validation_report(sim_input: PnSimInput, reason: str) -> PnValidationReport:
    """Build appropriate skip report for ineligible analytic validation."""
    if validation_skip_kind(sim_input, reason) == ValidationStatus.NUMERICAL_ONLY:
        return numerical_only_validation_report(reason)
    return unavailable_validation_report(reason)


def validation_run_passed(report: PnValidationReport | None) -> bool:
    """True when validation should not count as a run failure."""
    if report is None:
        return True
    if report.status in (ValidationStatus.UNAVAILABLE, ValidationStatus.NUMERICAL_ONLY):
        return True
    return report.status == ValidationStatus.ANALYTIC_PASSED
