"""Falling block simulator with RK4 stepping and probe callbacks."""

from __future__ import annotations

from typing import Callable

from autosim.models.base import DragModel, build_drag_model
from autosim.probes.registry import collect_probes
from autosim.schemas import (
    AgentDecision,
    ProbeSnapshot,
    SimInput,
    SimState,
    TrajectoryPoint,
    TrialResult,
)


def _acceleration(v: float, mass: float, gravity: float, drag_model: DragModel) -> float:
    """Altitude coordinate: y increases upward, v negative when falling."""
    drag = drag_model.drag_force(v)
    return -gravity + drag / mass


def _rk4_step(
    t: float,
    y: float,
    v: float,
    dt: float,
    mass: float,
    gravity: float,
    drag_model: DragModel,
) -> tuple[float, float, float]:
    def deriv(_t: float, _y: float, _v: float) -> tuple[float, float]:
        a = _acceleration(_v, mass, gravity, drag_model)
        return _v, a

    k1_y, k1_v = deriv(t, y, v)
    k2_y, k2_v = deriv(t + dt / 2, y + k1_y * dt / 2, v + k1_v * dt / 2)
    k3_y, k3_v = deriv(t + dt / 2, y + k2_y * dt / 2, v + k2_v * dt / 2)
    k4_y, k4_v = deriv(t + dt, y + k3_y * dt, v + k3_v * dt)

    new_y = y + (dt / 6) * (k1_y + 2 * k2_y + 2 * k3_y + k4_y)
    new_v = v + (dt / 6) * (k1_v + 2 * k2_v + 2 * k3_v + k4_v)
    new_a = _acceleration(new_v, mass, gravity, drag_model)
    return t + dt, new_y, new_v, new_a


def simulate_falling_block(
    sim_input: SimInput,
    on_probe: Callable[[ProbeSnapshot], AgentDecision | None] | None = None,
    trial_index: int = 0,
) -> TrialResult:
    drag_model = build_drag_model(sim_input.drag_model, sim_input.drag_params)
    m = sim_input.mass
    g = sim_input.gravity

    t = 0.0
    y = sim_input.y0
    v = sim_input.v0
    a = _acceleration(v, m, g, drag_model)

    initial_energy = 0.5 * m * v**2 + m * g * y
    trajectory: list[TrajectoryPoint] = []
    probes: list[ProbeSnapshot] = []
    decisions: list[AgentDecision] = []
    early_stopped = False
    stop_reason = "completed"
    next_probe_time = 0.0

    def record_state() -> ProbeSnapshot:
        state = SimState(t=t, y=y, v=v, a=a)
        drag = drag_model.drag_force(v)
        return collect_probes(state, sim_input, drag_model, drag, initial_energy)

    while t < sim_input.t_max:
        drag = drag_model.drag_force(v)
        trajectory.append(
            TrajectoryPoint(t=t, y=y, v=v, a=a, drag_force=drag)
        )

        if t >= next_probe_time - 1e-12:
            probe = record_state()
            probes.append(probe)
            next_probe_time += sim_input.probe_interval

            if on_probe is not None:
                decision = on_probe(probe)
                if decision is not None:
                    decisions.append(decision)
                    if decision.action.value == "early_stop":
                        early_stopped = True
                        stop_reason = decision.reason
                        break

            if probe.is_nan:
                early_stopped = True
                stop_reason = "NaN detected"
                break
            if probe.is_diverging:
                early_stopped = True
                stop_reason = "Divergence detected"
                break

        if y <= sim_input.ground_y:
            break

        t, y, v, a = _rk4_step(t, y, v, sim_input.dt, m, g, drag_model)

    impact_time = t if y <= sim_input.ground_y else None
    impact_velocity = v if y <= sim_input.ground_y else None

    terminal_velocity_estimate = None
    if len(probes) >= 2:
        terminal_velocity_estimate = probes[-1].v

    final_probe = record_state() if not probes or probes[-1].t != t else probes[-1]

    return TrialResult(
        trial_index=trial_index,
        input=sim_input,
        trajectory=trajectory,
        probes=probes,
        decisions=decisions,
        impact_time=impact_time,
        impact_velocity=impact_velocity,
        terminal_velocity_estimate=terminal_velocity_estimate,
        early_stopped=early_stopped,
        stop_reason=stop_reason,
        final_probe=final_probe,
    )
