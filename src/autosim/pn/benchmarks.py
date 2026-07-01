"""PN junction benchmark runner."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

from autosim.pn.schemas import PnRunConfig, ValidationStatus
from autosim.pn.solve import solve_pn

_BENCHMARKS_ROOT = Path(__file__).resolve().parents[3] / "benchmarks" / "pn"


def list_benchmark_cases() -> list[str]:
    if not _BENCHMARKS_ROOT.exists():
        return []
    return sorted(
        p.name for p in _BENCHMARKS_ROOT.iterdir()
        if p.is_dir() and (p / "config.yaml").exists()
    )


def load_benchmark_case(name: str) -> tuple[PnRunConfig, dict]:
    case_dir = _BENCHMARKS_ROOT / name
    if not case_dir.exists():
        raise FileNotFoundError(f"Benchmark case not found: {name}")
    with open(case_dir / "config.yaml", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    with open(case_dir / "reference.json", encoding="utf-8") as f:
        reference = json.load(f)
    return PnRunConfig.model_validate(config_data), reference


def run_benchmark(name: str) -> dict:
    config, reference = load_benchmark_case(name)
    sim_input = config.to_sim_input()

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

    tolerances = reference.get("tolerances", {})
    checks: dict[str, bool] = {}
    for key, ref_val in reference.get("metrics", {}).items():
        num = metrics.get(key)
        if num is None or ref_val is None:
            continue
        tol = tolerances.get(key, 0.4)
        if ref_val == 0:
            checks[key] = abs(num - ref_val) < tol
        else:
            checks[key] = abs(num - ref_val) / abs(ref_val) < tol
    if "converged" in reference:
        expected = reference["converged"]
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
        checks["sweep_points"] = metrics.get("sweep_points", 0) >= reference["min_sweep_points"]
    if reference.get("min_time_steps"):
        checks["time_steps"] = metrics.get("time_steps", 0) >= reference["min_time_steps"]

    validation_status = result.validation.status.value if result.validation else None
    if reference.get("require_analytic_validation") and result.validation:
        checks["analytic_validation"] = result.validation.status == ValidationStatus.ANALYTIC_PASSED

    run_ok = all(checks.values()) if checks else bool(metrics.get("converged"))
    return {
        "case": name,
        "metrics": metrics,
        "checks": checks,
        "all_passed": run_ok,
        "validation_status": validation_status,
        "validation": result.validation.model_dump() if result.validation else None,
    }
