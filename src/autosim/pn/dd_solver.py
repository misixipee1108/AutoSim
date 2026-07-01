"""1D drift-diffusion solver with Gummel iteration."""

from __future__ import annotations

from typing import Callable

import numpy as np
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve

from autosim.materials.loader import load_material
from autosim.pn.analytical import contact_potentials, depletion_psi_profile
from autosim.pn.breakdown import breakdown_assessment
from autosim.pn.doping.factory import build_doping_array, bulk_doping_concentrations, get_doping_profile
from autosim.pn.mesh import build_mesh
from autosim.pn.poisson_solver import solve_pn_poisson
from autosim.pn.postprocess import carrier_densities, electric_field, finalize_result, space_charge
from autosim.pn.recombination import total_recombination
from autosim.pn.schemas import PnAgentDecision, PnNewtonProbe, PnSimInput, PnTrialResult
from autosim.pn.solvers.gummel import run_gummel_loop


def _contact_carrier_bc(Na: float, Nd: float, ni: float) -> tuple[float, float, float, float]:
    """Ideal ohmic contacts: n_p = ni^2/Na, p_p = Na; n_n = Nd, p_n = ni^2/Nd."""
    n_left = ni**2 / max(Na, ni)
    p_left = Na
    n_right = Nd
    p_right = ni**2 / max(Nd, ni)
    return n_left, p_left, n_right, p_right


def _solve_carrier_line(
    psi: np.ndarray,
    x: np.ndarray,
    n_bc: tuple[float, float],
    p_bc: tuple[float, float],
    material,
    C: np.ndarray,
    R: np.ndarray,
    is_electron: bool,
) -> np.ndarray:
    """Tridiagonal solve for n or p with drift-diffusion flux (upwind) and recombination."""
    N = len(psi)
    mu = material.mu_n if is_electron else material.mu_p
    q = material.q
    Vt = material.Vt
    E = electric_field(psi, x)
    carrier = np.zeros(N)
    carrier[0] = n_bc[0] if is_electron else p_bc[0]
    carrier[-1] = n_bc[1] if is_electron else p_bc[1]

    if N <= 2:
        return carrier

    diag = np.zeros(N)
    lower = np.zeros(N - 1)
    upper = np.zeros(N - 1)
    rhs = np.zeros(N)

    for i in range(1, N - 1):
        dx_m = x[i] - x[i - 1]
        dx_p = x[i + 1] - x[i]
        dx_avg = 0.5 * (dx_m + dx_p)
        Em = 0.5 * (E[i - 1] + E[i])
        Ep = 0.5 * (E[i] + E[i + 1])
        sign = 1.0 if is_electron else -1.0
        gm = mu * sign * Em / dx_m
        gp = mu * sign * Ep / dx_p
        diff_m = mu * Vt / dx_m
        diff_p = mu * Vt / dx_p
        diag[i] = -(diff_m + diff_p + gm + gp)
        lower[i - 1] = diff_m + min(gm, 0.0)
        upper[i] = diff_p + max(gp, 0.0)
        rhs[i] = -q * R[i] * dx_avg

    diag[0] = 1.0
    diag[-1] = 1.0
    rhs[0] = carrier[0]
    rhs[-1] = carrier[-1]
    J = diags([lower, diag, upper], [-1, 0, 1], format="csr")
    return spsolve(J, rhs)


def _terminal_current(
    x: np.ndarray, psi: np.ndarray, n: np.ndarray, p: np.ndarray, material
) -> float:
    E = electric_field(psi, x)
    mu_n, mu_p = material.mu_n, material.mu_p
    q, Vt = material.q, material.Vt
    if len(x) < 3:
        return 0.0
    idx = len(x) - 2
    dn = (n[idx + 1] - n[idx]) / (x[idx + 1] - x[idx])
    dp = (p[idx + 1] - p[idx]) / (x[idx + 1] - x[idx])
    Jn = q * mu_n * (n[idx] * E[idx] - Vt * dn)
    Jp = q * mu_p * (p[idx] * E[idx] + Vt * dp)
    return float(Jn + Jp)


def solve_dd_gummel(
    sim_input: PnSimInput,
    on_probe: Callable[[PnNewtonProbe], PnAgentDecision | None] | None = None,
    trial_index: int = 0,
    psi_initial: np.ndarray | None = None,
    max_gummel: int = 25,
    gummel_tol: float = 5e-3,
) -> PnTrialResult:
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
    n_guess = p_guess = None
    all_probes: list[PnNewtonProbe] = []
    decisions: list[PnAgentDecision] = []
    if sim_input.recombination.enabled:
        max_gummel = max(max_gummel, 35)
        gummel_tol = max(gummel_tol, 0.05)

    def poisson_solve(n_fix, p_fix, outer):
        nonlocal all_probes
        result = solve_pn_poisson(
            sim_input,
            on_probe=on_probe,
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
        if not sim_input.recombination.enabled:
            n_new, p_new = n_boltz, p_boltz
        else:
            if n_old is None:
                n_old, p_old = n_boltz, p_boltz
            R, _ = total_recombination(n_old, p_old, material.ni, sim_input.recombination)
            n_new = _solve_carrier_line(psi, x, (n_l, n_r), (p_l, p_r), material, C, R, True)
            p_new = _solve_carrier_line(psi, x, (p_l, p_r), (n_l, n_r), material, C, R, False)
            n_new = np.maximum(n_new, 1.0)
            p_new = np.maximum(p_new, 1.0)
            relax = 0.5
            n_new = relax * n_new + (1.0 - relax) * n_old
            p_new = relax * p_new + (1.0 - relax) * p_old
        if n_old is None:
            return n_new, p_new, 1.0
        norm = float(np.max(np.abs(n_new - n_old) / np.maximum(n_old, 1.0)))
        norm = max(norm, float(np.max(np.abs(p_new - p_old) / np.maximum(p_old, 1.0))))
        return n_new, p_new, norm

    psi, n, p, _, gummel_ok, gummel_iters = run_gummel_loop(
        sim_input,
        poisson_solve,
        carrier_update,
        max_gummel=max_gummel,
        gummel_tol=gummel_tol,
    )

    rho = space_charge(n, p, C, material.q)
    J = _terminal_current(x, psi, n, p, material)
    bd = breakdown_assessment(electric_field(psi, x), x, sim_input.breakdown, J)
    if bd["breakdown_risk"]:
        J = float(bd["J_mult"])

    result = finalize_result(
        sim_input, material, x, psi, C, all_probes, decisions,
        newton_iterations=len(all_probes),
        converged=gummel_ok,
        early_stopped=not gummel_ok,
        stop_reason="gummel_converged" if gummel_ok else "gummel_not_converged",
        trial_index=trial_index,
    )
    result.model_type = "drift_diffusion"
    result.J_terminal = J
    result.M_ionization = float(bd["M_ionization"])
    result.breakdown_risk = bool(bd["breakdown_risk"])
    R, rstats = total_recombination(n, p, material.ni, sim_input.recombination)
    result.R_max = rstats["R_max"]
    return result
