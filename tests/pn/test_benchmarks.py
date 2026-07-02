"""Benchmark tests for PN junction cases."""

from __future__ import annotations

import pytest

from autosim.pn.benchmarks import list_benchmark_cases, run_benchmark_case, run_benchmark_suite


@pytest.mark.parametrize("case_name", list_benchmark_cases())
def test_benchmark_case(case_name: str):
    result = run_benchmark_case(case_name)
    assert result.outcome != "fail", (
        f"Benchmark {case_name} failed: {result.failure_reason} checks={result.checks}"
    )


def test_benchmark_list_non_empty():
    cases = list_benchmark_cases()
    assert len(cases) >= 5


def test_benchmark_suite_integration(tmp_path):
    suite = run_benchmark_suite(
        case_ids=["symmetric_equilibrium"],
        output_dir=tmp_path / "bench",
    )
    assert suite.summary.total == 1
    assert (tmp_path / "bench" / "benchmark_report.json").exists()
    assert (tmp_path / "bench" / "benchmark_report.schema.json").exists()
    assert suite.report is not None
    assert suite.report.summary.overall_passed is True