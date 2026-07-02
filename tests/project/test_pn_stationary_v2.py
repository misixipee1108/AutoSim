"""Tests for SimulationProject v2 PN stationary equivalence."""

from __future__ import annotations

from pathlib import Path

import pytest

from autosim.api.adapters.pn import PnAdapter
from autosim.api.adapters.project import ProjectAdapter
from autosim.plugins.physics.semiconductor_1d_poisson.compat import legacy_flat_to_project, project_to_pn_sim_input
from autosim.pn.schemas import PnRunConfig
from autosim.project.loader import default_pn_stationary_project, load_project
from autosim.project.tree_schema import build_model_tree_schema


EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "projects" / "pn_si_stationary_v2.json"


def test_default_template_validates():
    project = default_pn_stationary_project()
    assert project.schema_version == "2.0"
    assert project.active_study_id == "stat_equilibrium"
    assert len(project.model.physics_interfaces) == 1


def test_example_json_loads():
    project = load_project(EXAMPLE)
    assert project.project_id == "pn_si_equilibrium_demo"


def test_tree_schema_has_three_roots():
    project = default_pn_stationary_project()
    tree = build_model_tree_schema(project)
    assert len(tree["roots"]) == 3
    labels = [r["label"] for r in tree["roots"]]
    assert labels == ["Model", "Simulation", "Results"]


def test_v2_project_matches_legacy_config():
    legacy_flat = {
        "model_type": "poisson",
        "material": "Si",
        "temperature_k": 300.0,
        "Na": 1e18,
        "Nd": 1e16,
        "Lp": 2e-4,
        "Ln": 2e-4,
        "xj": 0.0,
        "Nx": 400,
        "Vapp": 0.0,
        "tol": 1e-4,
        "max_iter": 200,
        "damping": 0.5,
        "exp_clamp": 40.0,
        "doping": {"type": "abrupt"},
        "solver": {
            "method": "damped_newton",
            "convergence": {"criterion": "both", "relative_tol": 1e-4, "scaling_mode": "auto"},
        },
    }

    legacy_config = PnRunConfig.model_validate(legacy_flat)
    legacy_input = legacy_config.to_sim_input()
    legacy_result = PnAdapter().run_trial(legacy_config)

    project = legacy_flat_to_project(legacy_flat)
    study = project.studies[0]
    instance = project.model.physics_interfaces[0]
    v2_input = project_to_pn_sim_input(project, study, instance)

    assert v2_input.model_type == legacy_input.model_type
    assert v2_input.Na == legacy_input.Na
    assert v2_input.Nd == legacy_input.Nd
    assert v2_input.Nx == legacy_input.Nx
    assert v2_input.Vapp == legacy_input.Vapp
    assert abs(v2_input.tol - legacy_input.tol) < 1e-12

    adapter = ProjectAdapter()
    v2_result = adapter.run_study(project)
    assert v2_result.converged == legacy_result.converged
    assert v2_result.Vbi_numeric is not None
    assert legacy_result.Vbi_numeric is not None
    assert abs(v2_result.Vbi_numeric - legacy_result.Vbi_numeric) / legacy_result.Vbi_numeric < 0.01
    assert len(v2_result.profile) == len(legacy_result.profile)
    for a, b in zip(v2_result.profile, legacy_result.profile, strict=True):
        assert abs(a.psi - b.psi) < 1e-6


def test_project_adapter_normalize_result():
    project = default_pn_stationary_project()
    adapter = ProjectAdapter()
    raw = adapter.run_study(project)
    unified = adapter.normalize_result("test-run", project, raw)
    assert unified.profiles
    assert any(p.name == "potential" for p in unified.profiles)
    assert "Vbi" in unified.scalars


def test_example_runs_via_project_adapter():
    project = load_project(EXAMPLE)
    adapter = ProjectAdapter()
    raw = adapter.run_study(project)
    assert raw.converged or raw.solver_status.value in ("converged", "analytic_complete")
