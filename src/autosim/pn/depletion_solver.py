"""Standalone depletion-approximation solver."""

from __future__ import annotations

from typing import Callable

import numpy as np

from autosim.pn.analytical import contact_potentials, depletion_psi_profile, depletion_width
from autosim.pn.doping.factory import bulk_doping_concentrations, get_doping_profile
from autosim.materials.loader import load_material
from autosim.pn.mesh import build_mesh
from autosim.pn.postprocess import finalize_result
from autosim.pn.schemas import PnAgentDecision, PnNewtonProbe, PnSimInput, PnTrialResult


def _build_doping_array(x: np.ndarray, doping) -> np.ndarray:
    return np.array([doping.net_doping(float(xi)) for xi in x])


def solve_pn_depletion(
    sim_input: PnSimInput,
    on_probe: Callable[[PnNewtonProbe], object] | None = None,
    trial_index: int = 0,
) -> PnTrialResult:
    """Analytic depletion approximation — no Newton iteration."""
    material = load_material(sim_input.material, sim_input.temperature_k)
    doping = get_doping_profile(sim_input)
    Na, Nd = bulk_doping_concentrations(sim_input)
    jr = sim_input.junction_refinement
    x, _ = build_mesh(
        sim_input.Lp,
        sim_input.Ln,
        sim_input.Nx,
        junction_refinement=jr.enabled,
        refinement_ratio=jr.ratio,
        width_frac=jr.width_frac,
    )
    C = _build_doping_array(x, doping)
    psi = depletion_psi_profile(x, Na, Nd, material, sim_input.Vapp)

    dep = depletion_width(Na, Nd, material, sim_input.Vapp)
    psi_p, psi_n = contact_potentials(Na, Nd, material, sim_input.Vapp)
    Emax = dep.Emax

    probe = PnNewtonProbe(
        iteration=0,
        residual_norm=0.0,
        residual_reduction_rate=1.0,
        delta_norm=0.0,
        damping_factor=1.0,
        jacobian_condition_estimate=1.0,
        max_psi=float(np.max(psi)),
        min_psi=float(np.min(psi)),
        max_electric_field=Emax,
        max_carrier_density=0.0,
        min_n=0.0,
        min_p=0.0,
        charge_neutrality_error=0.0,
        is_nan=False,
        is_unphysical=False,
        exp_clamped=False,
        stalled=False,
        convergence_status="converged",
        failure_reason="",
    )
    if on_probe is not None:
        on_probe(probe)

    result = finalize_result(
        sim_input,
        material,
        x,
        psi,
        C,
        probes=[probe],
        decisions=[],
        newton_iterations=0,
        converged=True,
        early_stopped=False,
        stop_reason="depletion_analytic",
        trial_index=trial_index,
    )
    result.stop_reason = "depletion_analytic"
    return result
