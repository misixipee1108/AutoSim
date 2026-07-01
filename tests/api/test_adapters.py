"""Tests for API adapters and model registry."""

from __future__ import annotations

import pytest

from autosim.api.adapters.falling_block import FallingBlockAdapter
from autosim.api.adapters.pn import PnAdapter
from autosim.api.model_registry.registry import get_model, list_models
from autosim.api.schemas import RunStatus, UnifiedAction
from autosim.orchestrator.pn_runner import run_pn_trial
from autosim.orchestrator.runner import run_trial
from autosim.pn.schemas import PnSimInput
from autosim.schemas import SimInput


def test_list_models():
    models = list_models()
    ids = {m.model_id for m in models}
    assert "falling_block" in ids
    assert "pn_junction_1d" in ids


def test_get_model_descriptor():
    desc = get_model("pn_junction_1d")
    assert desc.model_name == "1D PN Junction"
    assert any(p.name == "Na" for p in desc.parameters)
    assert desc.default_config["Na"] == 1e18


def test_pn_descriptor_exposes_materials_and_solvers():
    desc = get_model("pn_junction_1d")
    material = next(p for p in desc.parameters if p.name == "material")
    solver = next(p for p in desc.parameters if p.name == "solver.method")
    model_type = next(p for p in desc.parameters if p.name == "model_type")
    doping = next(p for p in desc.parameters if p.name == "doping.type")

    mat_values = {o["value"] for o in (material.options or [])}
    assert {"Si", "Ge"}.issubset(mat_values)

    solver_values = {o["value"] for o in (solver.options or [])}
    assert "damped_newton" in solver_values
    assert "newton_line_search" in solver_values

    assert model_type.type == "select"
    assert doping.type == "select"
    assert any(n.id == "physics" for n in desc.tree_nodes)


def test_pn_adapter_accepts_solver_and_material_from_ui_config():
    adapter = PnAdapter()
    cfg = adapter.validate_config({
        "material": "Ge",
        "model_type": "depletion",
        "doping": {"type": "gaussian"},
        "solver": {"method": "newton_line_search", "adaptive_damping": True},
    })
    sim = cfg.to_sim_input()
    assert sim.material == "Ge"
    assert sim.model_type == "depletion"
    assert sim.doping is not None
    assert sim.doping.type == "gaussian"
    assert sim.solver.method == "newton_line_search"
    assert sim.solver.adaptive_damping is True
def test_falling_block_normalize():
    adapter = FallingBlockAdapter()
    from autosim.schemas import AgentBackend, AgentConfig

    sim = SimInput(
        mass=1.0,
        gravity=9.81,
        y0=10.0,
        t_max=5.0,
        probe_interval=0.5,
        dt=0.01,
        drag_params={"c2": 0.5},
        agent=AgentConfig(backend=AgentBackend.RULES),
    )
    result = run_trial(sim)
    unified = adapter.normalize_result("test-run", result)
    assert unified.model_id == "falling_block"
    assert len(unified.time_series) >= 2
    assert len(unified.convergence) == 1
    assert unified.convergence[0].name == "energy_drift"
    if result.impact_time:
        assert "impact_time" in unified.scalars


def test_pn_normalize():
    adapter = PnAdapter()
    from autosim.schemas import AgentBackend

    sim = PnSimInput(
        Na=1e18,
        Nd=1e16,
        Nx=100,
        tol=1e-3,
        max_iter=50,
        agent={"backend": AgentBackend.RULES},
    )
    result = run_pn_trial(sim)
    unified = adapter.normalize_result("test-pn", result)
    assert unified.model_id == "pn_junction_1d"
    assert len(unified.profiles) >= 3
    assert len(unified.convergence) == 3
    assert unified.convergence_summary is not None
    assert unified.convergence_summary.criterion == "both"
    assert unified.convergence_summary.relative_tol == 1e-3
    assert "Vbi" in unified.scalars or result.Vbi_numeric is not None


def test_agent_action_normalization():
    from autosim.schemas import AgentAction, AgentDecision

    fb = FallingBlockAdapter()
    dec = fb.normalize_decision(
        AgentDecision(action=AgentAction.RECOMMEND_NEXT, reason="test", suggested_params={"mass": 2.0})
    )
    assert dec.action == UnifiedAction.RECOMMEND_NEXT
    assert dec.raw_action == "recommend_next"

    from autosim.pn.schemas import PnAgentAction, PnAgentDecision

    pn = PnAdapter()
    pdec = pn.normalize_decision(
        PnAgentDecision(action=PnAgentAction.REFINE_MESH, reason="mesh too coarse")
    )
    assert pdec.action == UnifiedAction.REFINE_MESH


def test_validate_config_flatten():
    adapter = FallingBlockAdapter()
    config = adapter.validate_config({"agent.backend": "rules", "mass": 2.0})
    assert config.mass == 2.0
    assert config.agent.backend.value == "rules"

    pn = PnAdapter()
    pconfig = pn.validate_config({"Na": 1e17, "iteration.max_trials": 2})
    assert pconfig.Na == 1e17
    assert pconfig.iteration.max_trials == 2
