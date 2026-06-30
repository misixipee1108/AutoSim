"""Common probes shared by all drag models."""

from __future__ import annotations

from autosim.schemas import SimInput, SimState


def compute_common_probes(
    state: SimState,
    sim_input: SimInput,
    drag_force: float,
    initial_energy: float,
    v_max: float,
) -> dict:
    m = sim_input.mass
    g = sim_input.gravity
    ke = 0.5 * m * state.v**2
    pe = m * g * state.y
    total = ke + pe
    energy_drift = abs(total - initial_energy)
    distance = state.y - sim_input.ground_y

    is_nan = any(
        x != x  # NaN check
        for x in (state.t, state.y, state.v, state.a, drag_force)
    )
    is_diverging = abs(state.v) > v_max or energy_drift > sim_input.agent.energy_drift_max

    return {
        "t": state.t,
        "y": state.y,
        "v": state.v,
        "a": state.a,
        "ke": ke,
        "pe": pe,
        "energy_drift": energy_drift,
        "distance_to_ground": distance,
        "is_diverging": is_diverging,
        "is_nan": is_nan,
        "drag_force": drag_force,
    }
