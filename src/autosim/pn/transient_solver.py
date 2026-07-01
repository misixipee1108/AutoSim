"""Transient drift-diffusion with time-varying bias."""

from __future__ import annotations

from typing import Callable

import numpy as np

from autosim.pn.dd_solver import solve_dd_gummel
from autosim.pn.schemas import PnAgentDecision, PnNewtonProbe, PnSimInput, PnTrialResult, ProfilePoint


def vapp_at(t: float, spec) -> float:
    if spec.waveform == "step":
        return spec.Vapp_final if t >= 0 else spec.Vapp_initial
    if spec.waveform == "pulse":
        if spec.pulse_start <= t <= spec.pulse_start + spec.pulse_width:
            return spec.Vapp_final
        return spec.Vapp_initial
    if spec.waveform == "ramp":
        frac = min(max(t / max(spec.t_max, 1e-20), 0.0), 1.0)
        return spec.Vapp_initial + frac * (spec.Vapp_final - spec.Vapp_initial)
    return spec.Vapp_final


def solve_transient_dd(
    sim_input: PnSimInput,
    on_probe: Callable[[PnNewtonProbe], PnAgentDecision | None] | None = None,
    trial_index: int = 0,
) -> PnTrialResult:
    spec = sim_input.transient
    if not spec.enabled:
        return solve_dd_gummel(sim_input, on_probe=on_probe, trial_index=trial_index)

    t = 0.0
    dt = spec.dt
    series: list[dict] = []
    last: PnTrialResult | None = None
    psi_warm = None

    while t <= spec.t_max + dt * 0.5:
        vapp = vapp_at(t, spec)
        step_input = sim_input.model_copy_with_params({"Vapp": vapp})
        last = solve_dd_gummel(
            step_input,
            on_probe=on_probe if t == 0 else None,
            trial_index=trial_index,
            psi_initial=psi_warm,
            max_gummel=8,
        )
        if last.profile:
            psi_warm = np.array([p.psi for p in last.profile])
        mid = last.profile[len(last.profile) // 2] if last.profile else None
        series.append({
            "t": t,
            "Vapp": vapp,
            "J": last.J_terminal,
            "psi_mid": mid.psi if mid else 0.0,
            "n_mid": mid.n if mid else 0.0,
        })
        t += dt

    if last is None:
        last = solve_dd_gummel(sim_input, trial_index=trial_index)
    last.model_type = "transient_dd"
    last.time_series = series
    last.stop_reason = "transient_complete"
    return last
