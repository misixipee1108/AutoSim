"""Recombination model tests."""

import numpy as np

from autosim.pn.recombination import auger_recombination, radiative_recombination, srh_recombination, total_recombination
from autosim.pn.schemas import RecombinationSpec


def test_srh_zero_at_equilibrium():
    ni = 1e10
    n = np.array([ni * 10])
    p = np.array([ni * 0.1])
    r = srh_recombination(n, p, ni, 1e-6, 1e-6, ni, ni)
    assert abs(r[0]) < 1e-5 * ni


def test_total_recombination_disabled():
    n = np.array([1e15])
    p = np.array([1e12])
    r, stats = total_recombination(n, p, 1e10, RecombinationSpec(enabled=False))
    assert stats["R_max"] == 0.0
    assert np.all(r == 0)


def test_radiative_sign():
    ni = 1e10
    n = np.array([1e15])
    p = np.array([1e12])
    r = radiative_recombination(n, p, ni, 1e-15)
    assert r[0] > 0
