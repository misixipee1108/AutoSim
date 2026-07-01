"""Reverse bias PN junction tests."""

import numpy as np

from autosim.pn.analytical import depletion_width
from autosim.pn.materials import silicon_300k
from autosim.pn.poisson_solver import solve_pn_poisson
from autosim.pn.schemas import PnSimInput


def test_reverse_bias_converges():
    base = PnSimInput(
        Na=1e18,
        Nd=1e16,
        Lp=2e-4,
        Ln=2e-4,
        Nx=400,
        Vapp=0.0,
        tol=1e-4,
        max_iter=300,
        damping=0.5,
    )
    eq = solve_pn_poisson(base)
    psi0 = np.array([p.psi for p in eq.profile])
    rev_input = base.model_copy_with_params({"Vapp": -0.15})
    result = solve_pn_poisson(rev_input, psi_initial=psi0)
    assert result.W_numeric is not None
    assert result.W_rho_numeric is not None
    assert result.Emax_numeric is not None


def test_depletion_width_increases_with_reverse_bias():
    material = silicon_300k()
    base = PnSimInput(Na=1e18, Nd=1e16, Lp=2e-4, Ln=2e-4, Nx=400, tol=1e-4, max_iter=300, damping=0.5)
    eq = solve_pn_poisson(base.model_copy_with_params({"Vapp": 0.0}))
    psi0 = np.array([p.psi for p in eq.profile])
    rev = solve_pn_poisson(
        base.model_copy_with_params({"Vapp": -0.2}),
        psi_initial=psi0,
    )
    assert eq.W_rho_numeric is not None and rev.W_rho_numeric is not None
    assert rev.W_rho_numeric >= eq.W_rho_numeric

    w_eq = depletion_width(base.Na, base.Nd, material, 0.0).W
    w_rev = depletion_width(base.Na, base.Nd, material, -0.2).W
    assert w_rev > w_eq
