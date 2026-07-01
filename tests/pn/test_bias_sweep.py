"""Bias sweep tests."""

from autosim.pn.bias_sweep import build_vapp_list, run_bias_sweep
from autosim.pn.schemas import BiasScanSpec, PnSimInput


def test_build_vapp_list_range():
    spec = BiasScanSpec(enabled=True, Vapp_min=-1.0, Vapp_max=0.5, Vapp_step=0.5)
    values = build_vapp_list(spec)
    assert values == [-1.0, -0.5, 0.0, 0.5]


def test_bias_sweep_runs_all_points():
    sim_input = PnSimInput(
        Na=1e18,
        Nd=1e16,
        Nx=80,
        tol=1e-3,
        max_iter=100,
        bias_scan=BiasScanSpec(
            enabled=True,
            Vapp_list=[0.0, -0.3],
        ),
    )
    results, sweep = run_bias_sweep(sim_input)
    assert len(results) == 2
    assert len(sweep.points) == 2
    assert sweep.points[0].Vapp == 0.0
    assert sweep.points[1].Vapp == -0.3
    assert sweep.points[0].converged
