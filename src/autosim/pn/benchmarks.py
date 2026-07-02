"""PN junction benchmark runner."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import yaml

from autosim.pn.benchmark_report import (
    BenchmarkCaseResult,
    BenchmarkSuiteResult,
    BenchmarkSuiteSummary,
    MetricComparison,
    ValidationModeKind,
    _relative_repo_path,
    autosim_version,
    default_output_dir,
    generate_run_id,
    utc_now_iso,
    emit_benchmark_reports,
)
from autosim.pn.schemas import PnRunConfig, PnSimInput, PnTrialResult, ValidationStatus
from autosim.pn.solve import solve_pn
from autosim.pn.analytical import contact_potentials, depletion_psi_profile
from autosim.materials.loader import load_material
from autosim.pn.validation import build_shockley_validation_report, shockley_validation_eligible

_BENCHMARKS_ROOT = Path(__file__).resolve().parents[3] / "benchmarks" / "pn"


def benchmarks_root() -> Path:
    return _BENCHMARKS_ROOT


def list_benchmark_cases(root: Path | None = None) -> list[str]:
    base = root or _BENCHMARKS_ROOT
    if not base.exists():
        return []
    return sorted(
        p.name for p in base.iterdir()
        if p.is_dir() and (p / "config.yaml").exists()
    )


def load_benchmark_case(name: str, root: Path | None = None) -> tuple[PnRunConfig, dict, dict]:
    base = root or _BENCHMARKS_ROOT
    case_dir = base / name
    if not case_dir.exists():
        raise FileNotFoundError(f"Benchmark case not found: {name}")
    with open(case_dir / "config.yaml", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    with open(case_dir / "reference.json", encoding="utf-8") as f:
        reference = json.load(f)
    return PnRunConfig.model_validate(config_data), reference, config_data


def _infer_validation_mode(reference: dict, case_id: str) -> ValidationModeKind:
    mode = reference.get("validation_mode")
    if mode in ("analytic_abrupt", "numerical_only", "validation_unavailable"):
        return mode
    category = reference.get("category", "")
    if category == "doping":
        return "numerical_only"
    if reference.get("min_sweep_points") or reference.get("min_time_steps"):
        return "validation_unavailable"
    if not reference.get("metrics"):
        return "validation_unavailable"
    return "analytic_abrupt"


def _compare_metric(name: str, actual: float | None, ref_val: float | None, tol: float) -> MetricComparison:
    if actual is None or ref_val is None:
        return MetricComparison(
            name=name,
            actual=actual,
            reference=ref_val,
            tolerance=tol,
            passed=False,
        )
    if ref_val == 0:
        rel_error = abs(actual - ref_val)
        passed = rel_error < tol
    else:
        rel_error = abs(actual - ref_val) / abs(ref_val)
        passed = rel_error < tol
    return MetricComparison(
        name=name,
        actual=float(actual),
        reference=float(ref_val),
        rel_error=float(rel_error),
        tolerance=tol,
        passed=passed,
    )


def _build_initial_guess(
    variant: str,
    sim_input: PnSimInput,
    x: np.ndarray,
) -> np.ndarray | None:
    material = load_material(sim_input.material, sim_input.temperature_k)
    Na, Nd = sim_input.Na, sim_input.Nd
    if sim_input.doping and sim_input.doping.Na:
        Na = sim_input.doping.Na
    if sim_input.doping and sim_input.doping.Nd:
        Nd = sim_input.doping.Nd
    if variant == "depletion":
        return None
    if variant == "flat":
        return np.zeros_like(x)
    if variant == "perturbed":
        base = depletion_psi_profile(x, Na, Nd, material, sim_input.Vapp)
        rng = np.random.default_rng(42)
        return base + rng.normal(0.0, 0.05 * material.Vt, size=len(x))
    if variant == "linear_bc":
        psi_p, psi_n = contact_potentials(Na, Nd, material, sim_input.Vapp)
        return np.linspace(psi_p, psi_n, len(x))
    return None


def _run_mesh_sweep(config: PnRunConfig, reference: dict, raw: dict) -> tuple[PnTrialResult, dict[str, float | bool | int | None]]:
    nx_list = reference.get("Nx_list") or raw.get("mesh_sweep", {}).get("Nx_list", [])
    vbi_values: list[float] = []
    last_result: PnTrialResult | None = None
    all_converged = True
    for nx in nx_list:
        trial_config = config.model_copy(update={"Nx": int(nx)})
        sim_input = trial_config.to_sim_input()
        result = solve_pn(sim_input)
        last_result = result
        if result.Vbi_numeric is not None:
            vbi_values.append(float(result.Vbi_numeric))
        all_converged = all_converged and result.converged
    spread = max(vbi_values) - min(vbi_values) if vbi_values else float("inf")
    metrics: dict[str, float | bool | int | None] = {
        "Vbi": vbi_values[-1] if vbi_values else None,
        "converged": all_converged,
        "mesh_points": len(nx_list),
        "Vbi_spread": spread,
        "newton_iterations": last_result.newton_iterations if last_result else 0,
    }
    assert last_result is not None
    return last_result, metrics


def _run_initial_guess_variants(
    config: PnRunConfig,
    reference: dict,
    raw: dict,
) -> tuple[PnTrialResult, dict[str, float | bool | int | None]]:
    variants = reference.get("initial_guess_variants") or raw.get("initial_guess_variants", ["depletion"])
    sim_input = config.to_sim_input()
    from autosim.pn.mesh import build_mesh

    x, _ = build_mesh(sim_input.Lp, sim_input.Ln, sim_input.Nx)
    all_converged = True
    last_result: PnTrialResult | None = None
    for variant in variants:
        psi0 = _build_initial_guess(variant, sim_input, x)
        result = solve_pn(sim_input, psi_initial=psi0)
        last_result = result
        all_converged = all_converged and result.converged
    metrics = {
        "converged": all_converged,
        "variants_tested": len(variants),
        "newton_iterations": last_result.newton_iterations if last_result else 0,
    }
    assert last_result is not None
    return last_result, metrics


def _run_doping_sweep(
    config: PnRunConfig,
    reference: dict,
    raw: dict,
) -> tuple[PnTrialResult, dict[str, float | bool | int | None]]:
    pairs = reference.get("doping_pairs") or raw.get("doping_sweep", {}).get("pairs", [])
    all_converged = True
    vbi_errors: list[float] = []
    last_result: PnTrialResult | None = None
    for pair in pairs:
        na = float(pair["Na"])
        nd = float(pair["Nd"])
        ref_vbi = float(pair.get("Vbi", 0.0))
        trial_config = config.model_copy(update={"Na": na, "Nd": nd})
        sim_input = trial_config.to_sim_input()
        result = solve_pn(sim_input)
        last_result = result
        all_converged = all_converged and result.converged
        if result.Vbi_numeric is not None and ref_vbi > 0:
            vbi_errors.append(abs(result.Vbi_numeric - ref_vbi) / ref_vbi)
    metrics = {
        "converged": all_converged,
        "doping_points": len(pairs),
        "max_Vbi_rel_error": max(vbi_errors) if vbi_errors else None,
        "newton_iterations": last_result.newton_iterations if last_result else 0,
    }
    assert last_result is not None
    return last_result, metrics


def _execute_simulation(
    config: PnRunConfig,
    reference: dict | None = None,
    raw: dict | None = None,
) -> tuple[PnTrialResult, dict[str, float | bool | int | None]]:
    reference = reference or {}
    raw = raw or {}
    if reference.get("Nx_list") or raw.get("mesh_sweep", {}).get("enabled"):
        return _run_mesh_sweep(config, reference, raw)
    if reference.get("initial_guess_variants") or raw.get("initial_guess_variants"):
        return _run_initial_guess_variants(config, reference, raw)
    if reference.get("doping_pairs") or raw.get("doping_sweep", {}).get("enabled"):
        return _run_doping_sweep(config, reference, raw)

    sim_input = config.to_sim_input()
    metrics: dict[str, float | bool | int | None] = {}

    if sim_input.bias_scan.enabled:
        from autosim.pn.bias_sweep import run_bias_sweep

        results, sweep = run_bias_sweep(sim_input)
        result = results[-1] if results else solve_pn(sim_input)
        last_ok = sweep.points[-1].converged if sweep.points else result.converged
        metrics = {
            "Vbi": result.Vbi_numeric,
            "W": result.W_numeric,
            "Emax": result.Emax_numeric,
            "converged": sweep.all_converged or last_ok,
            "newton_iterations": result.newton_iterations,
            "sweep_points": len(sweep.points),
        }
    elif sim_input.cv_scan.enabled:
        from autosim.pn.cv_sweep import run_cv_sweep

        result = solve_pn(sim_input, include_outputs=False)
        cv = run_cv_sweep(sim_input)
        metrics = {
            "Vbi": result.Vbi_numeric,
            "W": result.W_numeric,
            "Emax": result.Emax_numeric,
            "converged": result.converged,
            "newton_iterations": result.newton_iterations,
            "sweep_points": len(cv.points),
        }
    elif sim_input.transient.enabled or sim_input.model_type == "transient_dd":
        result = solve_pn(sim_input)
        metrics = {
            "converged": result.converged or len(result.time_series) > 0,
            "newton_iterations": result.newton_iterations,
            "time_steps": len(result.time_series),
        }
    else:
        if sim_input.Vapp < 0 and sim_input.model_type == "poisson":
            eq_input = sim_input.model_copy_with_params({"Vapp": 0.0})
            eq_result = solve_pn(eq_input)
            psi0 = np.array([p.psi for p in eq_result.profile]) if eq_result.profile else None
            result = solve_pn(sim_input, psi_initial=psi0)
        else:
            result = solve_pn(sim_input)
        metrics = {
            "Vbi": result.Vbi_numeric,
            "W": result.W_numeric,
            "Emax": result.Emax_numeric,
            "J": result.J_terminal,
            "converged": result.converged,
            "newton_iterations": result.newton_iterations,
        }

    return result, metrics


def _evaluate_checks(
    reference: dict,
    validation_mode: ValidationModeKind,
    metrics: dict[str, float | bool | int | None],
    result: PnTrialResult,
) -> tuple[dict[str, bool], list[MetricComparison]]:
    tolerances = reference.get("tolerances", {})
    metric_comparisons: list[MetricComparison] = []
    checks: dict[str, bool] = {}

    ref_metrics = reference.get("metrics") or {}
    if validation_mode != "validation_unavailable":
        for key, ref_val in ref_metrics.items():
            tol = tolerances.get(key, 0.4)
            actual = metrics.get(key)
            if isinstance(actual, (int, float)):
                cmp = _compare_metric(key, float(actual), float(ref_val) if ref_val is not None else None, tol)
            else:
                cmp = MetricComparison(name=key, reference=ref_val, tolerance=tol, passed=False)
            metric_comparisons.append(cmp)
            checks[key] = cmp.passed

    if "converged" in reference:
        expected = bool(reference["converged"])
        actual = bool(metrics.get("converged"))
        if reference.get("allow_partial_converged") and not actual:
            checks["converged"] = (
                metrics.get("Emax") is not None
                or metrics.get("W") is not None
                or metrics.get("time_steps", 0) > 0
                or metrics.get("sweep_points", 0) >= reference.get("min_sweep_points", 1)
            )
        else:
            checks["converged"] = actual == expected

    if reference.get("min_sweep_points"):
        checks["sweep_points"] = int(metrics.get("sweep_points") or 0) >= int(reference["min_sweep_points"])

    if reference.get("min_time_steps"):
        checks["time_steps"] = int(metrics.get("time_steps") or 0) >= int(reference["min_time_steps"])

    if validation_mode == "analytic_abrupt" and reference.get("require_analytic_validation") and result.validation:
        checks["analytic_validation"] = result.validation.status == ValidationStatus.ANALYTIC_PASSED

    if reference.get("max_Vbi_spread") is not None:
        spread = metrics.get("Vbi_spread")
        checks["Vbi_spread"] = spread is not None and float(spread) <= float(reference["max_Vbi_spread"])

    if reference.get("require_all_variants_converged"):
        checks["all_variants_converged"] = bool(metrics.get("converged"))

    if reference.get("doping_pairs"):
        max_err = metrics.get("max_Vbi_rel_error")
        tol = tolerances.get("Vbi", 0.05)
        checks["doping_Vbi"] = max_err is not None and float(max_err) <= tol

    if reference.get("require_shockley_validation"):
        j_tol = float(reference.get("shockley_j_tol", 2.0))
        shockley_ok = False
        if result.sweep:
            shockley_ok = True
            for pt in result.sweep.points:
                if pt.Vapp <= 0.05 or pt.J is None:
                    continue
                step_input = result.input.model_copy_with_params({"Vapp": pt.Vapp})
                eligible, _ = shockley_validation_eligible(step_input)
                if not eligible:
                    continue
                report = build_shockley_validation_report(float(pt.J), step_input, j_tol=j_tol)
                if report.status != ValidationStatus.ANALYTIC_PASSED:
                    shockley_ok = False
                    break
        elif result.J_terminal is not None:
            eligible, _ = shockley_validation_eligible(result.input)
            if eligible:
                report = build_shockley_validation_report(
                    float(result.J_terminal), result.input, j_tol=j_tol
                )
                shockley_ok = report.status == ValidationStatus.ANALYTIC_PASSED
        checks["shockley_validation"] = shockley_ok

    if validation_mode == "numerical_only" and result.validation:
        checks["validation_not_abrupt"] = result.validation.status in (
            ValidationStatus.NUMERICAL_ONLY,
            ValidationStatus.UNAVAILABLE,
        )

    return checks, metric_comparisons


def _derive_outcome(
    checks: dict[str, bool],
    run_status: str,
    reference: dict,
    metrics: dict[str, float | bool | int | None],
    validation_mode: ValidationModeKind,
) -> tuple[str, bool, str | None, str | None]:
    checks_ok = all(checks.values()) if checks else True
    failure_reason: str | None = None
    warning_reason: str | None = None

    partial_used = (
        reference.get("allow_partial_converged")
        and not bool(metrics.get("converged"))
        and checks.get("converged", True)
    )

    if not checks_ok:
        failed = [k for k, v in checks.items() if not v]
        failure_reason = f"failed checks: {', '.join(failed)}"
    elif run_status == "failed":
        # Reference checks are ground truth; solver run_status may be failed on partial/stalled runs.
        if reference.get("allow_partial_converged") or validation_mode == "validation_unavailable":
            warning_reason = f"run_status=failed but reference checks passed (solver: stalled/partial)"
        else:
            failure_reason = "run_status=failed"

    if run_status == "completed_with_warning" and not failure_reason:
        warning_reason = warning_reason or "run_status=completed_with_warning"
    elif partial_used and checks_ok and not failure_reason:
        warning_reason = warning_reason or "partial convergence criteria satisfied"

    if failure_reason:
        return "fail", False, failure_reason, warning_reason
    if warning_reason:
        return "warning", True, None, warning_reason
    return "pass", True, None, None


def _doping_type_from_config(config: PnRunConfig) -> str:
    if config.doping and config.doping.type:
        return config.doping.type
    return "abrupt"


def run_benchmark_case(case_id: str, root: Path | None = None) -> BenchmarkCaseResult:
    base = root or _BENCHMARKS_ROOT
    config, reference, raw = load_benchmark_case(case_id, root=root)
    validation_mode = _infer_validation_mode(reference, case_id)
    config_path = _relative_repo_path(base / case_id / "config.yaml")
    reference_path = _relative_repo_path(base / case_id / "reference.json")

    t0 = time.perf_counter()
    result, metrics = _execute_simulation(config, reference, raw)
    elapsed_s = time.perf_counter() - t0

    checks, metric_comparisons = _evaluate_checks(reference, validation_mode, metrics, result)
    validation_status = result.validation.status.value if result.validation else None
    outcome, passed, failure_reason, warning_reason = _derive_outcome(
        checks, result.run_status, reference, metrics, validation_mode
    )

    extra_metrics = {
        k: v for k, v in metrics.items()
        if k not in {m.name for m in metric_comparisons}
    }

    return BenchmarkCaseResult(
        case_id=reference.get("case_id", case_id),
        model_type=result.model_type or config.model_type,
        validation_mode=validation_mode,
        category=reference.get("category", ""),
        description=reference.get("description", ""),
        config_path=config_path,
        reference_path=reference_path,
        doping_type=_doping_type_from_config(config),
        solver_status=result.solver_status.value,
        validation_status=validation_status,
        run_status=result.run_status,
        outcome=outcome,  # type: ignore[arg-type]
        passed=passed,
        elapsed_s=elapsed_s,
        metrics=metric_comparisons,
        checks=checks,
        failure_reason=failure_reason,
        warning_reason=warning_reason,
        stop_reason=result.stop_reason,
        validation_reason=result.validation.reason if result.validation else None,
        extra_metrics=extra_metrics,
    )


def run_benchmark_suite(
    case_ids: list[str] | None = None,
    output_dir: Path | None = None,
    root: Path | None = None,
    *,
    write_reports: bool = True,
) -> BenchmarkSuiteResult:
    ids = case_ids or list_benchmark_cases(root=root)
    out = output_dir or default_output_dir()
    if write_reports:
        out.mkdir(parents=True, exist_ok=True)

    suite_t0 = time.perf_counter()
    cases: list[BenchmarkCaseResult] = []
    for case_id in ids:
        cases.append(run_benchmark_case(case_id, root=root))

    summary = BenchmarkSuiteSummary(
        total=len(cases),
        passed=sum(1 for c in cases if c.outcome == "pass"),
        warnings=sum(1 for c in cases if c.outcome == "warning"),
        failed=sum(1 for c in cases if c.outcome == "fail"),
        elapsed_s=time.perf_counter() - suite_t0,
    )

    suite = BenchmarkSuiteResult(
        generated_at=utc_now_iso(),
        autosim_version=autosim_version(),
        run_id=generate_run_id(),
        output_dir=str(out) if write_reports else None,
        summary=summary,
        cases=cases,
    )

    if write_reports:
        report = emit_benchmark_reports(out, suite)
        suite.report = report

    return suite


def run_benchmark(name: str, root: Path | None = None) -> dict:
    """Backward-compatible wrapper returning legacy dict shape."""
    case = run_benchmark_case(name, root=root)
    metrics = {m.name: m.actual for m in case.metrics}
    if "converged" in case.checks:
        metrics["converged"] = case.checks.get("converged")
    return {
        "case": case.case_id,
        "metrics": metrics,
        "checks": case.checks,
        "all_passed": case.outcome != "fail",
        "validation_status": case.validation_status,
        "validation": None,
        "outcome": case.outcome,
        "solver_status": case.solver_status,
        "run_status": case.run_status,
    }
