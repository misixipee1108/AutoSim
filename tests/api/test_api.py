"""Tests for FastAPI v2 endpoints."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from autosim.api.main import app
from autosim.project.templates import falling_body_template, pn_si_stationary_template

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_project_templates():
    r = client.get("/api/project/templates")
    assert r.status_code == 200
    templates = r.json()
    assert len(templates) >= 2
    ids = {t["template_id"] for t in templates}
    assert "pn_stationary" in ids
    assert "falling_body" in ids


def test_list_physics_plugins():
    r = client.get("/api/plugins/physics")
    assert r.status_code == 200
    plugins = r.json()
    interface_ids = {p["interface_id"] for p in plugins}
    assert "semiconductor_1d_poisson" in interface_ids
    assert "mechanics_0d_falling_body" in interface_ids


def test_create_and_get_run_falling_block():
    project = falling_body_template().model_dump(mode="json")
    project["model"]["physics_interfaces"][0]["settings"]["t_max"] = 3.0
    project["model"]["physics_interfaces"][0]["settings"]["y0"] = 10.0
    r = client.post(
        "/api/runs",
        json={"project": project, "agent": "rules", "max_trials": 1},
    )
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    for _ in range(50):
        gr = client.get(f"/api/runs/{run_id}")
        assert gr.status_code == 200
        data = gr.json()
        if data["status"] in ("completed", "failed", "early_stopped"):
            assert data["model_id"] == "falling_body_v2"
            assert len(data.get("time_series", [])) > 0 or data.get("error")
            break
        time.sleep(0.2)
    else:
        raise AssertionError("Run did not complete in time")


def test_create_and_get_run_pn():
    project = pn_si_stationary_template().model_dump(mode="json")
    project["model"]["mesh"]["Nx"] = 80
    project["studies"][0]["solver_sequence"][0]["settings"]["relative_tol"] = 1e-3
    r = client.post(
        "/api/runs",
        json={"project": project, "agent": "rules", "max_trials": 1},
    )
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    for _ in range(80):
        gr = client.get(f"/api/runs/{run_id}")
        data = gr.json()
        if data["status"] in ("completed", "completed_with_warning", "failed", "early_stopped"):
            assert data["model_id"] == "pn_si_equilibrium_demo"
            assert data.get("convergence_summary") is not None or data["status"] == "failed"
            break
        time.sleep(0.2)
    else:
        raise AssertionError("PN run did not complete in time")
