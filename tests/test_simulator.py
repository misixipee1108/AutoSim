"""Tests for falling block simulator."""

import math

import pytest

from autosim.schemas import DragModelType, SimInput
from autosim.simulator.falling_block import simulate_falling_block


@pytest.fixture
def free_fall_input():
    return SimInput(
        mass=1.0,
        gravity=9.81,
        y0=100.0,
        v0=0.0,
        ground_y=0.0,
        drag_model=DragModelType.LINEAR,
        drag_params={"c1": 0.0},
        t_max=20.0,
        probe_interval=0.5,
        dt=0.01,
    )


def test_free_fall_impact_time(free_fall_input):
    result = simulate_falling_block(free_fall_input)
    # Analytic: y = 0.5 * g * t^2 => t = sqrt(2*100/9.81)
    expected_t = math.sqrt(2 * 100 / 9.81)
    assert result.impact_time is not None
    assert result.impact_time == pytest.approx(expected_t, rel=0.05)


def test_quadratic_terminal_velocity_convergence():
    sim_input = SimInput(
        drag_model=DragModelType.QUADRATIC,
        drag_params={"c2": 0.5},
        y0=1000.0,
        t_max=60.0,
        probe_interval=1.0,
    )
    result = simulate_falling_block(sim_input)
    v_term = math.sqrt(9.81 / 0.5)
    assert result.terminal_velocity_estimate is not None
    assert abs(result.terminal_velocity_estimate) == pytest.approx(v_term, rel=0.15)
