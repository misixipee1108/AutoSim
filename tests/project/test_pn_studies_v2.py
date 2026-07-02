"""Tests for PN study types via v2 project."""

from __future__ import annotations

from pathlib import Path

import pytest

from autosim.api.adapters.project import ProjectAdapter
from autosim.project.loader import load_project
from autosim.project.yaml_converter import pn_yaml_to_project

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"


@pytest.mark.parametrize(
    "yaml_name,study_type",
    [
        ("demo_pn_si_equilibrium.yaml", "parameter_sweep"),
        ("demo_pn_si_bias_sweep.yaml", "bias_sweep"),
        ("demo_pn_cv.yaml", "cv_sweep"),
        ("demo_pn_optimize.yaml", "optimization"),
    ],
)
def test_pn_yaml_study_type(yaml_name: str, study_type: str):
    project = pn_yaml_to_project(CONFIG / yaml_name)
    assert project.studies[0].study_type == study_type


def test_bias_sweep_project_runs():
    project = load_project(ROOT / "examples" / "projects" / "demo_pn_si_bias_sweep_v2.json")
    adapter = ProjectAdapter()
    raw = adapter.run_study(project)
    unified = adapter.normalize_result("sweep-test", project, raw)
    assert unified.sweep or unified.profiles


def test_iv_project_loads():
    project = load_project(ROOT / "examples" / "projects" / "demo_pn_iv_v2.json")
    assert project.model.physics_interfaces[0].interface_id == "semiconductor_1d_dd"
    assert project.studies[0].study_type == "bias_sweep"
