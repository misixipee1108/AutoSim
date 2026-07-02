"""Tests for PN benchmark runner and report generation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import yaml

from autosim.pn.benchmark_report import (
    SCHEMA_VERSION,
    BenchmarkCaseResult,
    BenchmarkReport,
    BenchmarkSuiteResult,
    BenchmarkSuiteSummary,
    build_benchmark_report,
    default_output_dir,
    detect_git_commit,
    write_benchmark_report_json,
    write_benchmark_report_md,
)
from autosim.pn.benchmarks import (
    _derive_outcome,
    _evaluate_checks,
    _infer_validation_mode,
    run_benchmark_case,
    run_benchmark_suite,
)

REQUIRED_TOP_LEVEL = {
    "schema_version",
    "run_id",
    "timestamp",
    "git_commit",
    "benchmark_suite",
    "autosim_version",
    "output_dir",
    "environment",
    "summary",
    "case_results",
}

REQUIRED_CASE_FIELDS = {
    "case_id",
    "config_path",
    "reference_path",
    "model_type",
    "doping_type",
    "validation_mode",
    "solver_status",
    "validation_status",
    "run_status",
    "outcome",
    "key_metrics",
    "reference_metrics",
    "relative_errors",
    "tolerances",
    "checks",
    "warnings",
    "failure_reason",
    "runtime_s",
}

MD_SECTIONS = [
    "## Overall Conclusion",
    "## Failed Cases",
    "## Cases Without Analytic Validation",
    "## Recommendations",
]


def _write_case(
    root: Path,
    case_id: str,
    config: dict,
    reference: dict,
) -> None:
    case_dir = root / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    with open(case_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f)
    with open(case_dir / "reference.json", "w", encoding="utf-8") as f:
        json.dump(reference, f, indent=2)


def _minimal_poisson_config(**overrides) -> dict:
    base = {
        "model_type": "poisson",
        "material": "Si",
        "Na": 1.0e16,
        "Nd": 1.0e16,
        "Nx": 80,
        "Vapp": 0.0,
        "tol": 1.0e-3,
        "max_iter": 200,
        "damping": 0.5,
    }
    base.update(overrides)
    return base


def test_infer_validation_mode():
    assert _infer_validation_mode({"validation_mode": "numerical_only"}, "x") == "numerical_only"
    assert _infer_validation_mode({"category": "doping"}, "x") == "numerical_only"
    assert _infer_validation_mode({"min_time_steps": 2}, "x") == "validation_unavailable"
    assert _infer_validation_mode({"metrics": {"Vbi": 1.0}}, "x") == "analytic_abrupt"


def test_derive_outcome_pass():
    outcome, passed, fail, _ = _derive_outcome(
        {"Vbi": True}, "completed", {}, {"converged": True}, "analytic_abrupt"
    )
    assert outcome == "pass"
    assert passed is True
    assert fail is None


def test_derive_outcome_fail():
    outcome, passed, fail, _ = _derive_outcome(
        {"Vbi": False}, "completed", {}, {"converged": True}, "analytic_abrupt"
    )
    assert outcome == "fail"
    assert passed is False
    assert "Vbi" in fail


def test_derive_outcome_warning_partial():
    outcome, passed, fail, warn = _derive_outcome(
        {"converged": True},
        "completed",
        {"allow_partial_converged": True},
        {"converged": False},
        "validation_unavailable",
    )
    assert outcome == "warning"
    assert passed is True
    assert fail is None
    assert "partial" in warn


def test_default_output_dir():
    path = default_output_dir()
    parts = path.as_posix().split("/")
    assert "reports" in parts
    assert "benchmarks" in parts


def test_git_commit_optional():
    with patch("autosim.pn.benchmark_report.subprocess.run", side_effect=OSError("no git")):
        assert detect_git_commit() is None


def test_fake_case_pass(tmp_path: Path):
    _write_case(
        tmp_path,
        "pass_case",
        _minimal_poisson_config(),
        {
            "case_id": "pass_case",
            "validation_mode": "analytic_abrupt",
            "metrics": {"Vbi": 0.7},
            "tolerances": {"Vbi": 0.5},
            "converged": True,
        },
    )
    result = run_benchmark_case("pass_case", root=tmp_path)
    assert result.outcome in ("pass", "warning")
    assert result.config_path.endswith("pass_case/config.yaml")
    assert result.doping_type == "abrupt"
    assert result.elapsed_s > 0


def test_fake_case_fail_bad_reference(tmp_path: Path):
    _write_case(
        tmp_path,
        "fail_case",
        _minimal_poisson_config(),
        {
            "case_id": "fail_case",
            "validation_mode": "analytic_abrupt",
            "metrics": {"Vbi": 999.0},
            "tolerances": {"Vbi": 0.001},
            "converged": True,
        },
    )
    result = run_benchmark_case("fail_case", root=tmp_path)
    assert result.outcome == "fail"
    assert result.failure_reason is not None


def test_fake_case_non_convergence(tmp_path: Path):
    _write_case(
        tmp_path,
        "no_conv",
        _minimal_poisson_config(Na=1.0e18, Nd=1.0e16, Nx=40, tol=1.0e-12, max_iter=2),
        {
            "case_id": "no_conv",
            "validation_mode": "analytic_abrupt",
            "converged": True,
        },
    )
    result = run_benchmark_case("no_conv", root=tmp_path)
    assert result.outcome == "fail"
    assert result.checks.get("converged") is False


def test_numerical_only_graded(tmp_path: Path):
    _write_case(
        tmp_path,
        "graded",
        _minimal_poisson_config(
            Na=1.0e18,
            Nd=1.0e16,
            Nx=100,
            doping={
                "type": "linear_graded",
                "Na": 1.0e18,
                "Nd": 1.0e16,
                "params": {"width": 1.0e-5},
            },
        ),
        {
            "case_id": "graded",
            "validation_mode": "numerical_only",
            "metrics": {"Vbi": 0.5},
            "tolerances": {"Vbi": 0.99},
            "converged": True,
        },
    )
    result = run_benchmark_case("graded", root=tmp_path)
    assert result.validation_mode == "numerical_only"
    assert result.validation_status == "numerical_only"
    assert result.doping_type == "linear_graded"
    assert result.checks.get("validation_not_abrupt") is True
    assert result.outcome != "fail" or "analytic" not in (result.failure_reason or "")


def test_validation_unavailable_transient(tmp_path: Path):
    _write_case(
        tmp_path,
        "transient",
        {
            "model_type": "transient_dd",
            "material": "Si",
            "Na": 1.0e18,
            "Nd": 1.0e16,
            "Nx": 60,
            "Vapp": 0.0,
            "tol": 1.0e-3,
            "max_iter": 50,
            "transient": {
                "enabled": True,
                "t_max": 2.0e-10,
                "dt": 1.0e-11,
                "waveform": "step",
                "Vapp_initial": 0.0,
                "Vapp_final": 0.3,
            },
        },
        {
            "case_id": "transient",
            "validation_mode": "validation_unavailable",
            "converged": True,
            "min_time_steps": 2,
        },
    )
    result = run_benchmark_case("transient", root=tmp_path)
    assert result.validation_mode == "validation_unavailable"
    assert not any(m.name in ("Vbi", "W") for m in result.metrics)
    assert "time_steps" in result.checks


def test_report_json_schema_fields(tmp_path: Path):
    _write_case(
        tmp_path,
        "schema_case",
        _minimal_poisson_config(Nx=60, max_iter=150),
        {"validation_mode": "analytic_abrupt", "converged": True},
    )
    out = tmp_path / "schema_out"
    suite = run_benchmark_suite(case_ids=["schema_case"], output_dir=out, root=tmp_path)
    data = json.loads((out / "benchmark_report.json").read_text(encoding="utf-8"))

    assert data["schema_version"] == SCHEMA_VERSION
    assert REQUIRED_TOP_LEVEL <= set(data.keys())
    assert data["summary"]["overall_passed"] is True
    assert len(data["case_results"]) == 1
    assert REQUIRED_CASE_FIELDS <= set(data["case_results"][0].keys())
    assert suite.report is not None
    assert suite.report.summary.overall_passed is True


def test_report_ci_overall_passed(tmp_path: Path):
    _write_case(tmp_path, "ok", _minimal_poisson_config(Nx=60), {"converged": True})
    _write_case(
        tmp_path,
        "bad",
        _minimal_poisson_config(),
        {"metrics": {"Vbi": 999.0}, "tolerances": {"Vbi": 0.001}, "converged": True},
    )

    ok_suite = run_benchmark_suite(case_ids=["ok"], output_dir=tmp_path / "ok_run", root=tmp_path)
    ok_data = json.loads((tmp_path / "ok_run" / "benchmark_report.json").read_text())
    assert ok_data["summary"]["overall_passed"] is True
    assert ok_suite.report.summary.overall_passed is True

    fail_suite = run_benchmark_suite(case_ids=["bad"], output_dir=tmp_path / "bad_run", root=tmp_path)
    fail_data = json.loads((tmp_path / "bad_run" / "benchmark_report.json").read_text())
    assert fail_data["summary"]["overall_passed"] is False
    assert fail_suite.summary.failed == 1


def test_report_markdown_sections(tmp_path: Path):
    _write_case(
        tmp_path,
        "md_case",
        _minimal_poisson_config(Nx=60),
        {"validation_mode": "analytic_abrupt", "converged": True},
    )
    out = tmp_path / "md_out"
    run_benchmark_suite(case_ids=["md_case"], output_dir=out, root=tmp_path)
    md = (out / "benchmark_report.md").read_text(encoding="utf-8")
    for section in MD_SECTIONS:
        assert section in md
    assert "PASS" in md or "WARN" in md


def test_custom_output_path(tmp_path: Path):
    _write_case(tmp_path, "custom", _minimal_poisson_config(Nx=60), {"converged": True})
    custom = tmp_path / "my_reports" / "run1"
    run_benchmark_suite(case_ids=["custom"], output_dir=custom, root=tmp_path)
    assert (custom / "benchmark_report.json").exists()
    data = json.loads((custom / "benchmark_report.json").read_text())
    assert data["output_dir"] == str(custom)


def test_report_writers_roundtrip(tmp_path: Path):
    suite = BenchmarkSuiteResult(
        generated_at="2026-01-01T00:00:00Z",
        autosim_version="0.1.0",
        run_id="20260101_000000_test0001",
        summary=BenchmarkSuiteSummary(total=1, passed=1, warnings=0, failed=0, elapsed_s=1.0),
        cases=[
            BenchmarkCaseResult(
                case_id="demo",
                model_type="poisson",
                config_path="benchmarks/pn/demo/config.yaml",
                reference_path="benchmarks/pn/demo/reference.json",
                doping_type="abrupt",
                solver_status="converged",
                validation_status="analytic_passed",
                run_status="completed",
                outcome="pass",
                passed=True,
                elapsed_s=0.5,
            )
        ],
    )
    report = build_benchmark_report(suite, output_dir=str(tmp_path))
    write_benchmark_report_json(tmp_path / "r.json", report)
    write_benchmark_report_md(tmp_path / "r.md", report)
    assert "demo" in (tmp_path / "r.md").read_text(encoding="utf-8")
    loaded = json.loads((tmp_path / "r.json").read_text())
    assert loaded["case_results"][0]["case_id"] == "demo"


def test_evaluate_checks_numerical_only_skips_abrupt_analytic():
    from autosim.pn.schemas import PnSimInput, PnTrialResult, PnValidationReport, ValidationStatus

    reference = {"metrics": {"Vbi": 0.8}, "tolerances": {"Vbi": 0.5}, "converged": True}
    sim = PnSimInput(Na=1e18, Nd=1e16)
    trial = PnTrialResult(
        input=sim,
        validation=PnValidationReport(status=ValidationStatus.NUMERICAL_ONLY, reason="graded"),
    )
    checks, _ = _evaluate_checks(
        reference,
        "numerical_only",
        {"Vbi": 0.81, "converged": True},
        trial,
    )
    assert checks["Vbi"] is True
    assert checks["validation_not_abrupt"] is True
