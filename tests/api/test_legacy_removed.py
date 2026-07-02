"""Assert legacy API endpoints are removed."""

from __future__ import annotations

from fastapi.testclient import TestClient

from autosim.api.main import app

client = TestClient(app)


def test_legacy_list_models_returns_410():
    r = client.get("/api/models")
    assert r.status_code == 410


def test_legacy_get_model_returns_410():
    r = client.get("/api/models/pn_junction_1d")
    assert r.status_code == 410


def test_legacy_run_body_returns_400():
    r = client.post(
        "/api/runs",
        json={
            "model_id": "pn_junction_1d",
            "config": {"Na": 1e18, "Nd": 1e16},
        },
    )
    assert r.status_code == 400
