"""Transient drift-diffusion with backward-Euler carrier terms."""

from __future__ import annotations

from typing import Callable

import numpy as np

from autosim.materials.loader import load_material
from autosim.pn.analytical import contact_potentials
from autosim.pn.dd_solver import (
    _contact_carrier_bc,
    _current_continuity_error,
    _solve_carrier_line,
    _terminal_current,
    solve_dd_gummel,
)
from autosim.pn.doping.factory import build_doping_array, bulk_doping_concentrations, get_doping_profile
from autosim.pn.mesh import build_mesh
from autosim.pn.poisson_solver import solve_pn_poisson
from autosim.pn.postprocess import carrier_densities, electric_field, finalize_result, space_charge
from autosim.pn.recombination import total_recombination
from autosim.pn.schemas import PnAgentDecision, PnNewtonProbe, PnSimInput, PnTrialResult
from autosim.pn.solvers.gummel import run_gummel_loop


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


def _transient_dd_step(
    sim_input: PnSimInput,
    n_prev: np.ndarray | None,
    p_prev: np.ndarray | None,
    dt: float,
    psi_initial: np.ndarray | None,
    on_probe: Callable[[PnNewtonProbe], PnAgentDecision | None] | None,
    trial_index: int,
) -> PnTrialResult:
    """Single transient step with backward-Euler carrier update."""
    material = load_material(sim_input.material, sim_input.temperature_k)
    doping = get_doping_profile(sim_input)
    Na, Nd = bulk_doping_concentrations(sim_input)
    jr = sim_input.junction_refinement
    x, _ = build_mesh(
        sim_input.Lp, sim_input.Ln, sim_input.Nx,
        junction_refinement=jr.enabled,
        refinement_ratio=jr.ratio,
        width_frac=jr.width_frac,
    )
    C = build_doping_array(x, doping)
    n_l, p_l, n_r, p_r = _contact_carrier_bc(Na, Nd, material.ni)
    all_probes: list[PnNewtonProbe] = []
    decisions: list[PnAgentDecision] = []

    def poisson_solve(n_fix, p_fix, outer):
        nonlocal all_probes
        result = solve_pn_poisson(
            sim_input,
            on_probe=on_probe if outer == 0 else None,
            trial_index=trial_index,
            psi_initial=psi_initial if outer == 0 else None,
            n_fixed=n_fix,
            p_fixed=p_fix,
        )
        psi = np.array([pt.psi for pt in result.profile])
        n = np.array([pt.n for pt in result.profile])
        p = np.array([pt.p for pt in result.profile])
        for pr in result.probes:
            pr.gummel_outer_iter = outer
        all_probes.extend(result.probes)
        decisions.extend(result.decisions)
        return psi, n, p, result.probes, result.converged

    def carrier_update(psi, n_old, p_old, outer):
        n_boltz, p_boltz, _ = carrier_densities(psi, material, sim_input.exp_clamp)
        if n_old is None:
            n_old, p_old = n_boltz, p_boltz
        n_ref, p_ref = (n_prev, p_prev) if n_prev is not None else (n_old, p_old)
        if sim_input.recombination.enabled:
            R, _ = total_recombination(n_old, p_old, material.ni, sim_input.recombination)
        else:
            R = np.zeros_like(psi)
        n_new = _solve_carrier_line(
            psi, x, (n_l, n_r), (p_l, p_r), material, C, R, True,
            n_old=n_ref, p_old=p_ref, dt=dt,
        )
        p_new = _solve_carrier_line(
            psi, x, (p_l, p_r), (n_l, n_r), material, C, R, False,
            n_old=n_ref, p_old=p_ref, dt=dt,
        )
        n_new = np.maximum(n_new, 1.0)
        p_new = np.maximum(p_new, 1.0)
        norm = float(np.max(np.abs(n_new - n_old) / np.maximum(n_old, 1.0)))
        norm = max(norm, float(np.max(np.abs(p_new - p_old) / np.maximum(p_old, 1.0))))
        return n_new, p_new, norm

    psi, n, p, _, gummel_ok, _ = run_gummel_loop(
        sim_input, poisson_solve, carrier_update, max_gummel=8, gummel_tol=0.05,
    )
    J = _terminal_current(x, psi, n, p, material)
    cc_err = _current_continuity_error(x, psi, n, p, material)
    if all_probes:
        all_probes[-1].current_continuity_error = cc_err

    result = finalize_result(
        sim_input, material, x, psi, C, all_probes, decisions,
        newton_iterations=len(all_probes),
        converged=gummel_ok,
        early_stopped=not gummel_ok,
        stop_reason="transient_step",
        trial_index=trial_index,
    )
    result.model_type = "transient_dd"
    result.J_terminal = J
    return result


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
    n_prev: np.ndarray | None = None
    p_prev: np.ndarray | None = None

    while t <= spec.t_max + dt * 0.5:
        vapp = vapp_at(t, spec)
        step_input = sim_input.model_copy_with_params({"Vapp": vapp})
        last = _transient_dd_step(
            step_input,
            n_prev,
            p_prev,
            dt,
            psi_warm,
            on_probe if t == 0 else None,
            trial_index,
        )
        if last.profile:
            psi_warm = np.array([p.psi for p in last.profile])
            n_prev = np.array([p.n for p in last.profile])
            p_prev = np.array([p.p for p in last.profile])
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
