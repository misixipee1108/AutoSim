"""Tests for physics plugins and internal adapters."""

from __future__ import annotations

import pytest

from autosim.api.adapters.falling_block import FallingBlockAdapter
from autosim.api.adapters.pn import PnAdapter
from autosim.api.schemas import RunStatus, UnifiedAction
from autosim.orchestrator.pn_runner import run_pn_trial
from autosim.orchestrator.runner import run_trial
from autosim.plugins.registry import get_physics_descriptor, list_physics_descriptors
from autosim.pn.schemas import PnSimInput
from autosim.schemas import SimInput


def test_list_physics_plugins():
    descriptors = list_physics_descriptors()
    ids = {d.interface_id for d in descriptors}
    assert "semiconductor_1d_poisson" in ids
    assert "semiconductor_1d_dd" in ids
    assert "mechanics_0d_falling_body" in ids


def test_pn_plugin_descriptor():
    desc = get_physics_descriptor("semiconductor_1d_poisson")
    assert desc.name == "Semiconductor 1D Poisson"
    assert any(p.name.endswith("doping.Na") for p in desc.parameter_schema)


def test_dd_plugin_descriptor():
    desc = get_physics_descriptor("semiconductor_1d_dd")
    assert "drift_diffusion" in str(desc.default_instance_config)


def test_falling_plugin_descriptor():
    desc = get_physics_descriptor("mechanics_0d_falling_body")
    assert desc.category == "mechanics"


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
    assert unified.status in (RunStatus.COMPLETED, RunStatus.EARLY_STOPPED)
    assert len(unified.time_series) > 0


def test_pn_adapter_normalize():
    adapter = PnAdapter()
    sim = PnSimInput(Na=1e18, Nd=1e16, Nx=80, tol=1e-3)
    result = run_pn_trial(sim)
    unified = adapter.normalize_result("test-run", result)
    assert unified.profiles
    assert "Vbi" in unified.scalars


def test_pn_agent_action_mapping():
    adapter = PnAdapter()
    from autosim.pn.schemas import PnAgentAction, PnAgentDecision

    dec = PnAgentDecision(action=PnAgentAction.REFINE_MESH, reason="test")
    unified = adapter.normalize_decision(dec)
    assert unified.action == UnifiedAction.REFINE_MESH
