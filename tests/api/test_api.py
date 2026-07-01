"""Tests for FastAPI endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from autosim.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_models():
    r = client.get("/api/models")
    assert r.status_code == 200
    models = r.json()
    assert len(models) >= 2


def test_get_model():
    r = client.get("/api/models/pn_junction_1d")
    assert r.status_code == 200
    assert r.json()["model_id"] == "pn_junction_1d"


def test_create_and_get_run_falling_block():
    r = client.post(
        "/api/runs",
        json={
            "model_id": "falling_block",
            "config": {"mass": 1.0, "y0": 10.0, "t_max": 3.0, "agent": {"backend": "rules"}},
            "agent": "rules",
            "max_trials": 1,
        },
    )
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    import time

    for _ in range(50):
        gr = client.get(f"/api/runs/{run_id}")
        assert gr.status_code == 200
        data = gr.json()
        if data["status"] in ("completed", "failed", "early_stopped"):
            assert data["model_id"] == "falling_block"
            assert len(data.get("time_series", [])) > 0 or data.get("error")
            break
        time.sleep(0.2)
    else:
        raise AssertionError("Run did not complete in time")


def test_create_and_get_run_pn():
    r = client.post(
        "/api/runs",
        json={
            "model_id": "pn_junction_1d",
            "config": {"Na": 1e18, "Nd": 1e16, "Nx": 80, "tol": 1e-3, "agent": {"backend": "rules"}},
            "agent": "rules",
            "max_trials": 1,
        },
    )
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    import time

    for _ in range(80):
        gr = client.get(f"/api/runs/{run_id}")
        data = gr.json()
        if data["status"] in ("completed", "completed_with_warning", "failed", "early_stopped"):
            assert data["model_id"] == "pn_junction_1d"
            assert data.get("convergence_summary") is not None or data["status"] == "failed"
            break
        time.sleep(0.2)
    else:
        raise AssertionError("PN run did not complete in time")
