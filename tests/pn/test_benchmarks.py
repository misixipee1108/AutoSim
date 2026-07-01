"""Benchmark tests for PN junction cases."""

from __future__ import annotations

import pytest

from autosim.pn.benchmarks import list_benchmark_cases, run_benchmark


@pytest.mark.parametrize("case_name", list_benchmark_cases())
def test_benchmark_case(case_name: str):
    result = run_benchmark(case_name)
    assert result["all_passed"], f"Benchmark {case_name} failed: {result['checks']}"


def test_benchmark_list_non_empty():
    cases = list_benchmark_cases()
    assert len(cases) >= 5
