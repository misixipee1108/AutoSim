"""Tests for material constants."""

import pytest

from autosim.pn.materials import silicon_300k, silicon_at_T


def test_silicon_300k_properties():
    mat = silicon_300k()
    assert mat.name == "Si"
    assert mat.eps_r == 11.7
    assert mat.ni == pytest.approx(1e10, rel=0.05)
    assert mat.Vt == pytest.approx(0.02585, rel=0.01)
    assert "Sze" in mat.source or "Green" in mat.source


def test_silicon_350k_ni_increases():
    mat300 = silicon_at_T(300.0)
    mat350 = silicon_at_T(350.0)
    assert mat350.ni > mat300.ni
    assert mat350.Vt == pytest.approx(0.03016, rel=0.01)


def test_gaas_material_loader():
    from autosim.materials.loader import load_material, list_materials

    assert "gaas" in list_materials()
    gaas = load_material("GaAs", 300.0)
    assert gaas.name == "GaAs"
    assert gaas.Eg_eV == pytest.approx(1.42, rel=0.01)
