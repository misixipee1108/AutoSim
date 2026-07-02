"""Tests for benchmark report API endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import yaml
from fastapi.testclient import TestClient

from autosim.api.main import app
from autosim.pn.benchmark_report import emit_benchmark_reports
from autosim.pn.benchmarks import run_benchmark_suite

client = TestClient(app)


def _write_case(root: Path, case_id: str, config: dict, reference: dict) -> None:
    case_dir = root / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    with open(case_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f)
    with open(case_dir / "reference.json", "w", encoding="utf-8") as f:
        json.dump(reference, f)


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


def _seed_reports(tmp_path: Path) -> tuple[str, str]:
    cases_root = tmp_path / "cases"
    out1 = tmp_path / "reports" / "20260101_120000"
    out2 = tmp_path / "reports" / "20260102_120000"

    _write_case(
        cases_root,
        "pass_case",
        _minimal_poisson_config(Nx=60),
        {"validation_mode": "analytic_abrupt", "converged": True},
    )
    _write_case(
        cases_root,
        "fail_case",
        _minimal_poisson_config(),
        {"metrics": {"Vbi": 999.0}, "tolerances": {"Vbi": 0.001}, "converged": True},
    )
    _write_case(
        cases_root,
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

    suite1 = run_benchmark_suite(
        case_ids=["pass_case", "graded"],
        output_dir=out1,
        root=cases_root,
    )
    suite2 = run_benchmark_suite(
        case_ids=["fail_case"],
        output_dir=out2,
        root=cases_root,
    )
    assert suite1.report is not None
    assert suite2.report is not None
    return suite1.report.run_id, suite2.report.run_id


def test_list_benchmark_reports(tmp_path: Path):
    run_id1, run_id2 = _seed_reports(tmp_path)
    reports_dir = tmp_path / "reports"

    with patch("autosim.api.benchmark_store.reports_root", return_value=reports_dir):
        r = client.get("/api/benchmarks/reports")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    run_ids = {item["run_id"] for item in data}
    assert run_id1 in run_ids
    assert run_id2 in run_ids
    assert data[0]["timestamp"] >= data[1]["timestamp"]


def test_get_benchmark_report_enriched(tmp_path: Path):
    run_id1, _ = _seed_reports(tmp_path)
    reports_dir = tmp_path / "reports"

    with patch("autosim.api.benchmark_store.reports_root", return_value=reports_dir):
        r = client.get(f"/api/benchmarks/reports/{run_id1}")
    assert r.status_code == 200
    data = r.json()
    assert data["run_id"] == run_id1
    assert len(data["case_results"]) == 2

    categories = {c["display_category"] for c in data["case_results"]}
    assert "passed" in categories or "numerical_only" in categories

    graded = next(c for c in data["case_results"] if c["case_id"] == "graded")
    assert graded["validation_mode"] == "numerical_only"
    assert graded["display_category"] == "numerical_only"
    assert graded["validation_status_display"] == "numerical_only"


def test_get_benchmark_report_markdown(tmp_path: Path):
    run_id1, _ = _seed_reports(tmp_path)
    reports_dir = tmp_path / "reports"

    with patch("autosim.api.benchmark_store.reports_root", return_value=reports_dir):
        r = client.get(f"/api/benchmarks/reports/{run_id1}/markdown")
    assert r.status_code == 200
    assert "## Overall Conclusion" in r.text
    assert "text/markdown" in r.headers.get("content-type", "")


def test_get_benchmark_report_not_found(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True)

    with patch("autosim.api.benchmark_store.reports_root", return_value=reports_dir):
        r = client.get("/api/benchmarks/reports/nonexistent")
    assert r.status_code == 404


def test_post_benchmark_run(tmp_path: Path):
    out = tmp_path / "reports" / "suite_run"
    with patch("autosim.pn.benchmarks.run_benchmark_suite") as mock_run:
        from autosim.pn.benchmark_report import BenchmarkSummary

        mock_run.return_value = type("Suite", (), {
            "run_id": "test_run_id",
            "output_dir": out,
            "summary": BenchmarkSummary(
                total=1,
                passed_count=1,
                warning_count=0,
                failed_count=0,
                total_runtime_s=1.0,
                overall_passed=True,
            ),
            "report": None,
        })()
        r = client.post("/api/benchmarks/run")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == "test_run_id"
    assert body["overall_passed"] is True
