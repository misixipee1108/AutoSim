"""Benchmark report models and writers."""

from __future__ import annotations

import json
import platform
import socket
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"

OutcomeKind = Literal["pass", "warning", "fail"]
ValidationModeKind = Literal["analytic_abrupt", "numerical_only", "validation_unavailable"]

REPO_ROOT = Path(__file__).resolve().parents[3]


class MetricComparison(BaseModel):
    name: str
    actual: float | None = None
    reference: float | None = None
    rel_error: float | None = None
    tolerance: float | None = None
    passed: bool = False


class BenchmarkCaseResult(BaseModel):
    case_id: str
    model_type: str
    validation_mode: ValidationModeKind = "analytic_abrupt"
    category: str = ""
    description: str = ""
    config_path: str = ""
    reference_path: str = ""
    doping_type: str = "abrupt"
    solver_status: str
    validation_status: str | None = None
    run_status: str
    outcome: OutcomeKind
    passed: bool
    elapsed_s: float
    metrics: list[MetricComparison] = Field(default_factory=list)
    checks: dict[str, bool] = Field(default_factory=dict)
    failure_reason: str | None = None
    warning_reason: str | None = None
    stop_reason: str | None = None
    validation_reason: str | None = None
    extra_metrics: dict[str, float | bool | int | None] = Field(default_factory=dict)


class BenchmarkSuiteSummary(BaseModel):
    total: int = 0
    passed: int = 0
    warnings: int = 0
    failed: int = 0
    elapsed_s: float = 0.0


class BenchmarkEnvironment(BaseModel):
    python_version: str
    platform: str
    hostname: str | None = None


class BenchmarkSummary(BaseModel):
    total: int
    passed_count: int
    warning_count: int
    failed_count: int
    total_runtime_s: float
    overall_passed: bool


class BenchmarkCaseReport(BaseModel):
    case_id: str
    config_path: str
    reference_path: str
    model_type: str
    doping_type: str
    validation_mode: ValidationModeKind
    category: str = ""
    description: str = ""
    solver_status: str
    validation_status: str | None = None
    run_status: str
    outcome: OutcomeKind
    key_metrics: dict[str, float | bool | int | None] = Field(default_factory=dict)
    reference_metrics: dict[str, float | bool | int | None] = Field(default_factory=dict)
    relative_errors: dict[str, float | None] = Field(default_factory=dict)
    tolerances: dict[str, float] = Field(default_factory=dict)
    checks: dict[str, bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    failure_reason: str | None = None
    runtime_s: float
    stop_reason: str | None = None


class BenchmarkReport(BaseModel):
    schema_version: str = SCHEMA_VERSION
    run_id: str
    timestamp: str
    git_commit: str | None
    benchmark_suite: str = "pn"
    autosim_version: str
    output_dir: str
    environment: BenchmarkEnvironment
    summary: BenchmarkSummary
    case_results: list[BenchmarkCaseReport] = Field(default_factory=list)


class BenchmarkSuiteResult(BaseModel):
    generated_at: str
    autosim_version: str
    run_id: str = ""
    output_dir: str | None = None
    summary: BenchmarkSuiteSummary
    cases: list[BenchmarkCaseResult] = Field(default_factory=list)
    report: BenchmarkReport | None = None

    @property
    def all_passed(self) -> bool:
        return self.summary.failed == 0


def _format_metric_value(value: float | bool | int | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if abs(value) >= 1e4 or (abs(value) < 1e-3 and value != 0):
        return f"{value:.4e}"
    return f"{value:.6g}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def generate_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{ts}_{uuid.uuid4().hex[:8]}"


def default_output_dir(base: str = "reports/benchmarks") -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return Path(base) / ts


def autosim_version() -> str:
    try:
        from importlib.metadata import version

        return version("autosim")
    except Exception:
        return "0.1.0"


def detect_git_commit(cwd: Path | None = None) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd or REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def collect_environment() -> BenchmarkEnvironment:
    hostname: str | None = None
    try:
        hostname = socket.gethostname()
    except OSError:
        pass
    return BenchmarkEnvironment(
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        hostname=hostname,
    )


def _relative_repo_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _case_warnings(case: BenchmarkCaseResult) -> list[str]:
    warnings: list[str] = []
    if case.warning_reason:
        warnings.append(case.warning_reason)
    if case.validation_reason:
        warnings.append(case.validation_reason)
    if case.validation_mode == "numerical_only":
        warnings.append("No abrupt analytic reference; frozen numerical reference used")
    elif case.validation_mode == "validation_unavailable":
        warnings.append("Analytic validation unavailable; behavioral checks only")
    return warnings


def case_result_to_report(case: BenchmarkCaseResult) -> BenchmarkCaseReport:
    key_metrics = {m.name: m.actual for m in case.metrics}
    key_metrics.update(case.extra_metrics)
    reference_metrics = {m.name: m.reference for m in case.metrics}
    relative_errors = {m.name: m.rel_error for m in case.metrics}
    tolerances = {
        m.name: m.tolerance for m in case.metrics if m.tolerance is not None
    }
    return BenchmarkCaseReport(
        case_id=case.case_id,
        config_path=case.config_path,
        reference_path=case.reference_path,
        model_type=case.model_type,
        doping_type=case.doping_type,
        validation_mode=case.validation_mode,
        category=case.category,
        description=case.description,
        solver_status=case.solver_status,
        validation_status=case.validation_status,
        run_status=case.run_status,
        outcome=case.outcome,
        key_metrics=key_metrics,
        reference_metrics=reference_metrics,
        relative_errors=relative_errors,
        tolerances=tolerances,
        checks=case.checks,
        warnings=_case_warnings(case),
        failure_reason=case.failure_reason,
        runtime_s=case.elapsed_s,
        stop_reason=case.stop_reason,
    )


def build_benchmark_report(
    suite: BenchmarkSuiteResult,
    *,
    run_id: str | None = None,
    output_dir: str,
    git_commit: str | None = None,
    benchmark_suite: str = "pn",
) -> BenchmarkReport:
    rid = run_id or suite.run_id or generate_run_id()
    case_reports = [case_result_to_report(c) for c in suite.cases]
    summary = BenchmarkSummary(
        total=suite.summary.total,
        passed_count=suite.summary.passed,
        warning_count=suite.summary.warnings,
        failed_count=suite.summary.failed,
        total_runtime_s=suite.summary.elapsed_s,
        overall_passed=suite.summary.failed == 0,
    )
    return BenchmarkReport(
        run_id=rid,
        timestamp=suite.generated_at,
        git_commit=git_commit,
        benchmark_suite=benchmark_suite,
        autosim_version=suite.autosim_version,
        output_dir=output_dir,
        environment=collect_environment(),
        summary=summary,
        case_results=case_reports,
    )


def _overall_conclusion(report: BenchmarkReport) -> str:
    if not report.summary.overall_passed:
        return "FAIL"
    if report.summary.warning_count > 0:
        return "PASS WITH WARNINGS"
    return "PASS"


def _build_recommendations(report: BenchmarkReport) -> list[str]:
    recs: list[str] = []
    failed = [c for c in report.case_results if c.outcome == "fail"]
    warned = [c for c in report.case_results if c.outcome == "warning"]
    non_analytic = [
        c for c in report.case_results
        if c.validation_mode in ("numerical_only", "validation_unavailable")
    ]
    solver_issues = [
        c for c in report.case_results
        if c.solver_status not in ("converged", "analytic_complete")
        or (c.stop_reason and c.stop_reason not in ("converged", "completed", "drift_diffusion_mvp"))
    ]

    if failed:
        recs.append(
            f"Investigate {len(failed)} failed case(s): "
            + ", ".join(c.case_id for c in failed[:5])
        )
    if warned:
        recs.append("Review warning cases for solver stability or relaxed tolerance drift")
    if any(c.validation_mode == "numerical_only" for c in non_analytic):
        recs.append(
            "Regenerate frozen reference metrics when graded/erfc physics or mesh changes"
        )
    if solver_issues:
        recs.append(
            "Check non-converged/stalled cases — consider warm-start, damping, or bias continuation"
        )
    if not recs:
        recs.append("No action required — all benchmark checks passed")
    return recs


def write_benchmark_report_json(path: Path, report: BenchmarkReport) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.model_dump(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def write_benchmark_report_schema(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(BenchmarkReport.model_json_schema(), indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def write_benchmark_report_md(path: Path, report: BenchmarkReport) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    conclusion = _overall_conclusion(report)
    s = report.summary
    lines: list[str] = [
        "# PN Benchmark Report",
        "",
        "## Overall Conclusion",
        "",
        f"**{conclusion}**",
        "",
        (
            f"The PN benchmark suite {'passed' if s.overall_passed else 'failed'} "
            f"with {s.passed_count} passed, {s.warning_count} warnings, "
            f"and {s.failed_count} failed out of {s.total} cases."
        ),
        "",
        "## Summary",
        "",
        "| Run ID | Timestamp | Git Commit | AutoSim | Runtime (s) |",
        "|--------|-----------|------------|---------|-------------:|",
        (
            f"| {report.run_id} | {report.timestamp} | "
            f"{report.git_commit or '—'} | {report.autosim_version} | {s.total_runtime_s:.2f} |"
        ),
        "",
        "| Total | Passed | Warnings | Failed | Overall Passed |",
        "|------:|-------:|---------:|-------:|:--------------:|",
        (
            f"| {s.total} | {s.passed_count} | {s.warning_count} | {s.failed_count} | "
            f"{'yes' if s.overall_passed else 'no'} |"
        ),
        "",
        f"**Environment:** Python {report.environment.python_version}, "
        f"{report.environment.platform}",
        "",
    ]

    failed_cases = [c for c in report.case_results if c.outcome == "fail"]
    lines.extend(["## Failures", ""])
    if not failed_cases:
        lines.append("_No failures._")
    else:
        lines.append(
            f"**{len(failed_cases)} case(s) failed.** See details below and in "
            "`failure_reason` fields of `benchmark_report.json`."
        )
        lines.append("")
        lines.append("| Case | Category | Failure Reason | Failed Checks | Solver |")
        lines.append("|------|----------|----------------|---------------|--------|")
        for c in failed_cases:
            failed_checks = [k for k, v in c.checks.items() if not v]
            lines.append(
                f"| {c.case_id} | {c.category or '—'} | {c.failure_reason or '—'} | "
                f"`{', '.join(failed_checks) or '—'}` | {c.solver_status} |"
            )
    lines.append("")

    lines.extend(["## Failed Cases", ""])
    if not failed_cases:
        lines.append("_No failed cases._")
    else:
        lines.append("| Case | Failure Reason | Failed Checks |")
        lines.append("|------|----------------|---------------|")
        for c in failed_cases:
            failed_checks = [k for k, v in c.checks.items() if not v]
            lines.append(
                f"| {c.case_id} | {c.failure_reason or '—'} | "
                f"`{', '.join(failed_checks) or '—'}` |"
            )
    lines.append("")

    warned_cases = [c for c in report.case_results if c.outcome == "warning"]
    lines.extend(["## Warnings", ""])
    if not warned_cases:
        lines.append("_No warning cases._")
    else:
        lines.append("| Case | Warnings |")
        lines.append("|------|----------|")
        for c in warned_cases:
            warn_text = "; ".join(c.warnings) if c.warnings else "—"
            lines.append(f"| {c.case_id} | {warn_text} |")
    lines.append("")

    metric_cases = [
        c for c in report.case_results
        if c.validation_mode in ("analytic_abrupt", "numerical_only") and c.key_metrics
    ]
    lines.extend(["## Key Metrics Comparison", ""])
    if not metric_cases:
        lines.append("_No metric comparisons._")
    else:
        lines.append("| Case | Metric | Actual | Reference | Rel. Error | Tol. | Pass |")
        lines.append("|------|--------|-------:|----------:|-----------:|-----:|:----:|")
        for c in metric_cases:
            for name, actual in c.key_metrics.items():
                if name in c.reference_metrics:
                    ref = c.reference_metrics.get(name)
                    rel = c.relative_errors.get(name)
                    tol = c.tolerances.get(name)
                    passed = c.checks.get(name, True)
                    rel_s = f"{rel:.4g}" if rel is not None else "—"
                    tol_s = f"{tol:.4g}" if tol is not None else "—"
                    lines.append(
                        f"| {c.case_id} | {name} | {_format_metric_value(actual)} | "
                        f"{_format_metric_value(ref)} | {rel_s} | {tol_s} | "
                        f"{'yes' if passed else 'no'} |"
                    )
    lines.append("")

    no_analytic = [
        c for c in report.case_results
        if c.validation_mode in ("numerical_only", "validation_unavailable")
    ]
    lines.extend(["## Cases Without Analytic Validation", ""])
    lines.append(
        "These cases do **not** use abrupt depletion analytic validation. "
        "They are not marked as failed solely because analytic validation is unavailable."
    )
    lines.append("")
    if not no_analytic:
        lines.append("_All cases use analytic or metric reference checks._")
    else:
        lines.append("| Case | Mode | Validation Status | Reason | Outcome |")
        lines.append("|------|------|-------------------|--------|---------|")
        for c in no_analytic:
            reason = "; ".join(c.warnings) if c.warnings else "—"
            lines.append(
                f"| {c.case_id} | {c.validation_mode} | "
                f"{c.validation_status or '—'} | {reason} | {c.outcome} |"
            )
    lines.append("")

    solver_issues = [
        c for c in report.case_results
        if c.solver_status not in ("converged", "analytic_complete")
        or (c.stop_reason and "stalled" in c.stop_reason.lower())
        or c.solver_status == "max_iter_reached"
    ]
    lines.extend(["## Non-Converged / Solver Issues", ""])
    if not solver_issues:
        lines.append("_No solver convergence issues detected._")
    else:
        lines.append("| Case | Solver Status | Stop Reason | Run Status | Outcome |")
        lines.append("|------|---------------|-------------|------------|---------|")
        for c in solver_issues:
            lines.append(
                f"| {c.case_id} | {c.solver_status} | {c.stop_reason or '—'} | "
                f"{c.run_status} | {c.outcome} |"
            )
    lines.append("")

    recs = _build_recommendations(report)
    lines.extend(["## Recommendations", ""])
    for rec in recs:
        lines.append(f"- {rec}")
    lines.append("")

    lines.extend([
        "## Full Case Index",
        "",
        "| Case | Model | Doping | Mode | Outcome | Solver | Validation | Run | Time (s) |",
        "|------|-------|--------|------|---------|--------|------------|-----|---------:|",
    ])
    for c in report.case_results:
        lines.append(
            f"| {c.case_id} | {c.model_type} | {c.doping_type} | {c.validation_mode} | "
            f"**{c.outcome}** | {c.solver_status} | {c.validation_status or '—'} | "
            f"{c.run_status} | {c.runtime_s:.2f} |"
        )
    lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def emit_benchmark_reports(output_dir: Path, suite: BenchmarkSuiteResult) -> BenchmarkReport:
    """Build v1 report and write JSON, Markdown, and JSON schema."""
    git_commit = detect_git_commit()
    run_id = suite.run_id or generate_run_id()
    report = build_benchmark_report(
        suite,
        run_id=run_id,
        output_dir=str(output_dir),
        git_commit=git_commit,
    )
    write_benchmark_report_json(output_dir / "benchmark_report.json", report)
    write_benchmark_report_md(output_dir / "benchmark_report.md", report)
    write_benchmark_report_schema(output_dir / "benchmark_report.schema.json")
    return report
