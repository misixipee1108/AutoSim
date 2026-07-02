"""Material library temperature dependence tests."""

from __future__ import annotations

import pytest


def _load_material(name: str = "Si", temperature_k: float = 300.0):
    import autosim.pn.solve  # noqa: F401 — break circular import via pn package init
    from autosim.materials.loader import load_material

    return load_material(name, temperature_k)


def _list_materials():
    import autosim.pn.solve  # noqa: F401
    from autosim.materials.loader import list_materials

    return list_materials()


def test_silicon_ni_increases_with_temperature():
    si_300 = _load_material("Si", 300.0)
    si_350 = _load_material("Si", 350.0)
    assert si_350.ni > si_300.ni


def test_silicon_mobility_temperature_dependence():
    si_300 = _load_material("Si", 300.0)
    si_400 = _load_material("Si", 400.0)
    assert si_400.mu_n < si_300.mu_n
    assert si_400.mu_p < si_300.mu_p


def test_gaas_material_loads():
    assert "gaas" in _list_materials()
    gaas = _load_material("GaAs", 300.0)
    assert gaas.name == "GaAs"
    assert gaas.eps_r == pytest.approx(12.9)
    assert gaas.ni < _load_material("Si", 300.0).ni


def test_gaas_mobility_at_elevated_temperature():
    gaas_300 = _load_material("GaAs", 300.0)
    gaas_400 = _load_material("GaAs", 400.0)
    assert gaas_400.mu_n < gaas_300.mu_n
    ratio = gaas_400.mu_n / gaas_300.mu_n
    expected = (400.0 / 300.0) ** (-2.4)
    assert ratio == pytest.approx(expected, rel=0.01)


def test_material_vt_scales_with_temperature():
    m = _load_material("Si", 300.0)
    m_hot = _load_material("Si", 400.0)
    assert m_hot.Vt > m.Vt
    assert m_hot.Vt / m.Vt == pytest.approx(400.0 / 300.0, rel=1e-3)
