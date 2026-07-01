"""Breakdown model tests."""

import numpy as np

from autosim.pn.breakdown import breakdown_assessment, impact_ionization_multiplier
from autosim.pn.schemas import BreakdownSpec


def test_breakdown_risk_when_emax_high():
    x = np.linspace(-1e-4, 1e-4, 50)
    E = np.linspace(0, 4e5, 50)
    bd = breakdown_assessment(E, x, BreakdownSpec(E_crit=3e5))
    assert bd["breakdown_risk"] is True
    assert bd["M_ionization"] >= 1.0


def test_no_breakdown_low_field():
    x = np.linspace(-1e-4, 1e-4, 20)
    E = np.ones(20) * 1e4
    bd = breakdown_assessment(E, x, BreakdownSpec())
    assert bd["breakdown_risk"] is False
