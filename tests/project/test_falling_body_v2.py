"""Tests for falling body v2 project path."""

from __future__ import annotations

from pathlib import Path

from autosim.api.adapters.project import ProjectAdapter
from autosim.project.loader import load_project
from autosim.project.templates import falling_body_template
from autosim.project.yaml_converter import falling_yaml_to_project

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "projects" / "demo_falling_block_v2.json"


def test_falling_template_validates():
    project = falling_body_template()
    assert project.schema_version == "2.0"
    assert project.model.physics_interfaces[0].interface_id == "mechanics_0d_falling_body"


def test_falling_yaml_converts():
    project = falling_yaml_to_project(
        Path(__file__).resolve().parents[2] / "config" / "demo_falling_block.yaml"
    )
    assert project.studies[0].study_type == "time_dependent"


def test_falling_runs_via_project_adapter():
    project = load_project(EXAMPLE)
    adapter = ProjectAdapter()
    raw = adapter.run_study(project)
    unified = adapter.normalize_result("fb-test", project, raw)
    assert len(unified.time_series) > 0
    assert unified.scalars.get("impact_time") or unified.scalars.get("impact_velocity")
