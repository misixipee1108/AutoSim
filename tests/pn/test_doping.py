"""Doping profile tests."""

from autosim.pn.doping.factory import get_doping_profile
from autosim.pn.schemas import DopingSpec, PnSimInput
from autosim.pn.solve import solve_pn


def test_abrupt_doping_default():
    inp = PnSimInput(Na=1e18, Nd=1e16, Nx=100, tol=1e-3, max_iter=50)
    doping = get_doping_profile(inp)
    assert doping.net_doping(-1e-4) < 0
    assert doping.net_doping(1e-4) > 0


def test_linear_graded_doping():
    inp = PnSimInput(
        Na=1e18,
        Nd=1e16,
        doping=DopingSpec(type="linear_graded", Na=1e18, Nd=1e16, params={"width": 1e-5}),
        Nx=150,
        tol=1e-3,
        max_iter=80,
    )
    result = solve_pn(inp)
    assert result.converged or result.stop_reason == "converged"


def test_gaussian_doping():
    inp = PnSimInput(
        Na=1e18,
        Nd=1e16,
        doping=DopingSpec(type="gaussian", Na=1e18, Nd=1e16, params={"sigma": 1e-5}),
        Nx=150,
        tol=1e-3,
        max_iter=80,
    )
    result = solve_pn(inp)
    assert len(result.profile) > 0


def test_depletion_solver_mode():
    inp = PnSimInput(model_type="depletion", Na=1e18, Nd=1e16, Nx=100)
    result = solve_pn(inp)
    assert result.converged
    assert result.newton_iterations == 0
