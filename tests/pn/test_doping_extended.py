"""Extended doping profile tests."""

from autosim.pn.doping.custom import CustomDoping
from autosim.pn.doping.erfc import ErfcDoping
from autosim.pn.doping.factory import get_doping_profile
from autosim.pn.doping.table import TableDoping
from autosim.pn.schemas import DopingSpec, PnSimInput


def test_erfc_doping_profile():
    d = ErfcDoping(Na=1e18, Nd=1e16, length=1e-5)
    assert d.net_doping(-1e-4) < 0
    assert d.net_doping(1e-4) > 0


def test_custom_doping_expression():
    d = CustomDoping("Nd if x > 0 else -Na", {"Na": 1e18, "Nd": 1e16})
    assert d.net_doping(-1e-5) < 0
    assert d.net_doping(1e-5) > 0


def test_table_doping_interpolation():
    d = TableDoping(points=[(-1e-4, -1e18), (0.0, 0.0), (1e-4, 1e16)])
    assert d.net_doping(-5e-5) < 0
    assert d.net_doping(5e-5) > 0


def test_factory_erfc_from_spec():
    inp = PnSimInput(
        Na=1e18,
        Nd=1e16,
        doping=DopingSpec(type="erfc", Na=1e18, Nd=1e16, params={"length": 1e-5}),
    )
    prof = get_doping_profile(inp)
    assert prof.net_doping(0.0) != 0.0
