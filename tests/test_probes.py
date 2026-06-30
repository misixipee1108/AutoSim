"""Tests for probe system."""

from autosim.models.base import build_drag_model
from autosim.probes.registry import collect_probes
from autosim.schemas import DragModelType, SimInput, SimState


def test_common_probes_fields():
    sim_input = SimInput(
        drag_model=DragModelType.QUADRATIC,
        drag_params={"c2": 0.5},
    )
    drag_model = build_drag_model(sim_input.drag_model, sim_input.drag_params)
    state = SimState(t=1.0, y=50.0, v=10.0, a=5.0)
    drag = drag_model.drag_force(state.v)
    initial_energy = 0.5 * sim_input.mass * state.v**2 + sim_input.mass * sim_input.gravity * state.y

    probe = collect_probes(state, sim_input, drag_model, drag, initial_energy)

    assert probe.t == 1.0
    assert probe.y == 50.0
    assert probe.v == 10.0
    assert probe.drag_force == drag
    assert "v_terminal_quad" in probe.theory_probes


def test_linear_theory_probes():
    sim_input = SimInput(
        drag_model=DragModelType.LINEAR,
        drag_params={"c1": 2.0},
    )
    drag_model = build_drag_model(sim_input.drag_model, sim_input.drag_params)
    state = SimState(t=0.0, y=100.0, v=5.0, a=0.0)
    drag = drag_model.drag_force(state.v)
    initial_energy = 1000.0

    probe = collect_probes(state, sim_input, drag_model, drag, initial_energy)
    assert "v_terminal_linear" in probe.theory_probes
    assert probe.theory_probes["v_terminal_linear"] == 4.905


def test_polynomial_theory_probes():
    sim_input = SimInput(
        drag_model=DragModelType.POLYNOMIAL,
        drag_params={"coeffs": [1.0, 0.5]},
    )
    drag_model = build_drag_model(sim_input.drag_model, sim_input.drag_params)
    state = SimState(t=0.0, y=50.0, v=10.0, a=0.0)
    drag = drag_model.drag_force(state.v)
    probe = collect_probes(state, sim_input, drag_model, drag, 500.0)
    assert "dominant_term" in probe.theory_probes
    assert "term_fractions" in probe.theory_probes


def test_diverging_probe():
    sim_input = SimInput(
        drag_model=DragModelType.LINEAR,
        drag_params={"c1": 0.01},
        agent={"v_max": 50.0},
    )
    drag_model = build_drag_model(sim_input.drag_model, sim_input.drag_params)
    state = SimState(t=1.0, y=10.0, v=100.0, a=0.0)
    drag = drag_model.drag_force(state.v)
    probe = collect_probes(state, sim_input, drag_model, drag, 1000.0)
    assert probe.is_diverging is True
