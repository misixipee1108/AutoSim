"""C-V sweep tests."""

from autosim.pn.cv_sweep import differential_capacitance, run_cv_sweep
from autosim.pn.schemas import CVScanSpec, PnSimInput
from autosim.pn.solve import solve_pn


def test_cv_sweep_runs():
    inp = PnSimInput(
        Nx=60,
        cv_scan=CVScanSpec(enabled=True, Vapp_min=-0.5, Vapp_max=0.0, Vapp_step=0.25, delta_V=0.05),
    )
    cv = run_cv_sweep(inp)
    assert len(cv.points) >= 2
    assert any(p.Cj_diff is not None for p in cv.points)


def test_differential_capacitance_positive():
    inp = PnSimInput(Nx=60, Vapp=-0.3)
    base = solve_pn(inp, include_outputs=False)
    c = differential_capacitance(inp, base, delta_V=0.05)
    assert c is not None
    assert c > 0
