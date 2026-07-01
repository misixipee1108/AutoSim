"""Transient solver tests."""

from autosim.pn.schemas import PnSimInput, TransientBiasSpec
from autosim.pn.transient_solver import solve_transient_dd, vapp_at


def test_vapp_step_waveform():
    spec = TransientBiasSpec(waveform="step", Vapp_initial=0.0, Vapp_final=0.5)
    assert vapp_at(0.0, spec) == 0.5
    assert vapp_at(-1.0, spec) == 0.0


def test_transient_produces_time_series():
    inp = PnSimInput(
        model_type="transient_dd",
        Nx=40,
        transient=TransientBiasSpec(
            enabled=True, t_max=1e-10, dt=5e-11, Vapp_final=0.1
        ),
    )
    result = solve_transient_dd(inp)
    assert len(result.time_series) >= 2
