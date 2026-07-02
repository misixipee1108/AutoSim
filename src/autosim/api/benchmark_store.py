"""Scan and serve PN benchmark reports from disk."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from autosim.pn.benchmark_report import REPO_ROOT, BenchmarkCaseReport, BenchmarkReport

DisplayCategory = Literal[
    "passed",
    "warning",
    "failed",
    "numerical_only",
    "validation_unavailable",
]


def reports_root() -> Path:
    env = os.environ.get("AUTOSIM_BENCHMARK_REPORTS_DIR")
    if env:
        return Path(env)
    return REPO_ROOT / "reports" / "benchmarks"


def validation_status_display(raw: str | None) -> str | None:
    if raw is None:
        return None
    mapping = {
        "analytic_passed": "passed",
        "analytic_failed": "failed",
        "numerical_only": "numerical_only",
        "unavailable": "unavailable",
    }
    return mapping.get(raw, raw)


def display_category(case: BenchmarkCaseReport) -> DisplayCategory:
    if case.outcome == "fail":
        return "failed"
    if case.validation_mode == "numerical_only":
        return "numerical_only"
    if case.validation_mode == "validation_unavailable":
        return "validation_unavailable"
    if case.outcome == "warning":
        return "warning"
    return "passed"


def _load_report_json(path: Path) -> BenchmarkReport:
    return BenchmarkReport.model_validate_json(path.read_text(encoding="utf-8"))


def _index_reports() -> dict[str, tuple[Path, BenchmarkReport]]:
    root = reports_root()
    if not root.is_dir():
        return {}

    indexed: dict[str, tuple[Path, BenchmarkReport]] = {}
    for child in sorted(root.iterdir(), reverse=True):
        if not child.is_dir():
            continue
        json_path = child / "benchmark_report.json"
        if not json_path.is_file():
            continue
        try:
            report = _load_report_json(json_path)
        except Exception:
            continue
        indexed[report.run_id] = (child, report)
        indexed[child.name] = (child, report)
    return indexed


def list_reports() -> list[BenchmarkReport]:
    seen: set[str] = set()
    out: list[BenchmarkReport] = []
    for _dir, report in _index_reports().values():
        if report.run_id in seen:
            continue
        seen.add(report.run_id)
        out.append(report)
    out.sort(key=lambda r: r.timestamp, reverse=True)
    return out


def resolve_report_dir(run_id: str) -> Path | None:
    entry = _index_reports().get(run_id)
    if entry is None:
        return None
    return entry[0]


def get_report(run_id: str) -> BenchmarkReport | None:
    entry = _index_reports().get(run_id)
    if entry is None:
        return None
    return entry[1]


def get_report_markdown(run_id: str) -> str | None:
    report_dir = resolve_report_dir(run_id)
    if report_dir is None:
        return None
    md_path = report_dir / "benchmark_report.md"
    if not md_path.is_file():
        return None
    return md_path.read_text(encoding="utf-8")
