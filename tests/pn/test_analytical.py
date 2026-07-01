"""Tests for analytical depletion formulas."""

import math

import pytest

from autosim.pn.analytical import built_in_potential, contact_potentials, depletion_width
from autosim.pn.materials import silicon_300k


@pytest.fixture
def material():
    return silicon_300k()


def test_built_in_potential_benchmark(material):
    Na, Nd = 1e18, 1e16
    Vbi = built_in_potential(Na, Nd, material)
    expected = material.Vt * math.log(Na * Nd / material.ni**2)
    assert Vbi == pytest.approx(expected)
    assert 0.80 < Vbi < 0.90


def test_depletion_width_equilibrium(material):
    Na, Nd = 1e18, 1e16
    result = depletion_width(Na, Nd, material, Vapp=0.0)
    assert result.W > 0
    assert result.Wp + result.Wn == pytest.approx(result.W, rel=1e-6)
    assert result.Emax == pytest.approx(2 * result.Vbi / result.W, rel=1e-6)


def test_contact_potential_difference_equals_vbi(material):
    Na, Nd = 1e18, 1e16
    psi_p, psi_n = contact_potentials(Na, Nd, material, Vapp=0.0)
    Vbi = built_in_potential(Na, Nd, material)
    assert psi_n - psi_p == pytest.approx(Vbi, rel=1e-6)
