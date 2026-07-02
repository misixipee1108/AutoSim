"""API tests for SimulationProject v2 endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from autosim.api.main import app

client = TestClient(app)


def test_project_tree_schema():
    resp = client.get("/api/project/tree-schema")
    assert resp.status_code == 200
    data = resp.json()
    assert data["schema_version"] == "2.0"
    assert len(data["roots"]) == 3


def test_pn_stationary_template():
    resp = client.get("/api/project/templates/pn_stationary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["schema_version"] == "2.0"
    assert data["project_id"] == "pn_si_equilibrium_demo"


def test_list_physics_plugins():
    resp = client.get("/api/plugins/physics")
    assert resp.status_code == 200
    plugins = resp.json()
    assert any(p["interface_id"] == "semiconductor_1d_poisson" for p in plugins)


def test_create_run_with_project():
    tpl = client.get("/api/project/templates/pn_stationary").json()
    resp = client.post(
        "/api/runs",
        json={"project": tpl, "agent": "rules"},
    )
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]
    result = client.get(f"/api/runs/{run_id}").json()
    assert result["status"] in ("completed", "completed_with_warning", "running", "pending")
    if result["status"] in ("completed", "completed_with_warning"):
        assert result.get("profiles")
