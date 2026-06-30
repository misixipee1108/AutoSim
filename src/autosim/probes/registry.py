"""Probe registry: collect common + theory-specific probes."""

from __future__ import annotations

from autosim.models.base import DragModel
from autosim.probes.common import compute_common_probes
from autosim.probes.theory import compute_theory_probes
from autosim.schemas import ProbeSnapshot, SimInput, SimState


def collect_probes(
    state: SimState,
    sim_input: SimInput,
    drag_model: DragModel,
    drag_force: float,
    initial_energy: float,
) -> ProbeSnapshot:
    common = compute_common_probes(
        state,
        sim_input,
        drag_force,
        initial_energy,
        sim_input.agent.v_max,
    )
    theory = compute_theory_probes(state, sim_input, drag_model)
    return ProbeSnapshot(
        **common,
        theory_probes=theory,
    )
