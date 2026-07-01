"""Doping profile factory."""

from __future__ import annotations

from typing import Any

import numpy as np

from autosim.pn.doping.abrupt import AbruptJunctionDoping
from autosim.pn.doping.custom import CustomDoping
from autosim.pn.doping.erfc import ErfcDoping
from autosim.pn.doping.gaussian import GaussianDoping
from autosim.pn.doping.linear_graded import LinearGradedDoping
from autosim.pn.doping.piecewise import PiecewiseDoping
from autosim.pn.doping.table import TableDoping
from autosim.pn.schemas import DopingSpec, PnSimInput


class ShiftedDoping:
    """Evaluate base profile at x - xj offset."""

    def __init__(self, inner, xj: float = 0.0) -> None:
        self.inner = inner
        self.xj = xj
        self.name = getattr(inner, "name", "shifted")

    def net_doping(self, x: float) -> float:
        return self.inner.net_doping(x - self.xj)

    def net_doping_array(self, x) -> np.ndarray:
        xs = np.asarray(x, dtype=float) - self.xj
        if hasattr(self.inner, "net_doping_array"):
            return np.asarray(self.inner.net_doping_array(xs), dtype=float)
        return np.array([self.inner.net_doping(float(xi)) for xi in xs])


def _wrap_xj(profile, xj: float):
    if abs(xj) < 1e-20:
        return profile
    return ShiftedDoping(profile, xj)


def get_doping_profile(sim_input: PnSimInput):
    """Build doping profile from sim input (doping spec or legacy Na/Nd)."""
    spec = sim_input.doping
    xj = sim_input.xj
    if spec is None or spec.type == "abrupt":
        Na = spec.Na if spec and spec.Na is not None else sim_input.Na
        Nd = spec.Nd if spec and spec.Nd is not None else sim_input.Nd
        return _wrap_xj(AbruptJunctionDoping(Na, Nd), xj)
    params = spec.params or {}
    Na = spec.Na if spec.Na is not None else sim_input.Na
    Nd = spec.Nd if spec.Nd is not None else sim_input.Nd
    if spec.type == "linear_graded":
        return _wrap_xj(LinearGradedDoping(Na, Nd, width=float(params.get("width", 1e-5))), xj)
    if spec.type == "gaussian":
        return _wrap_xj(GaussianDoping(Na, Nd, sigma=float(params.get("sigma", 1e-5))), xj)
    if spec.type == "piecewise":
        table = params.get("table") or params.get("points") or []
        points = [(float(p[0]), float(p[1])) for p in table]
        return _wrap_xj(PiecewiseDoping(points), xj)
    if spec.type == "erfc":
        length = float(params.get("length", params.get("L_diff", 1e-5)))
        return ErfcDoping(Na, Nd, xj=xj, length=length)
    if spec.type == "custom":
        expr = spec.expression or params.get("expression")
        if not expr:
            raise ValueError("custom doping requires 'expression'")
        custom_params = {k: float(v) for k, v in params.items() if k != "expression"}
        custom_params.setdefault("Na", Na)
        custom_params.setdefault("Nd", Nd)
        return _wrap_xj(CustomDoping(expr, custom_params), xj)
    if spec.type == "table":
        table = params.get("table") or params.get("points")
        file = spec.file or params.get("file")
        if table:
            points = [(float(p[0]), float(p[1])) for p in table]
            return _wrap_xj(TableDoping(points=points), xj)
        if file:
            return _wrap_xj(TableDoping(file=file), xj)
        raise ValueError("table doping requires 'file' or inline table points")
    raise ValueError(f"Unknown doping type: {spec.type}")


def build_doping_array(x: np.ndarray, doping) -> np.ndarray:
    if hasattr(doping, "net_doping_array"):
        return np.asarray(doping.net_doping_array(x), dtype=float)
    return np.array([doping.net_doping(float(xi)) for xi in x])


def bulk_doping_concentrations(sim_input: PnSimInput) -> tuple[float, float]:
    """Return (Na, Nd) bulk values for analytics and BCs."""
    doping = get_doping_profile(sim_input)
    Na = getattr(doping, "Na", None) or getattr(doping, "bulk_Na", None)
    Nd = getattr(doping, "Nd", None) or getattr(doping, "bulk_Nd", None)
    if Na is None:
        Na = getattr(getattr(doping, "inner", None), "Na", sim_input.Na)
    if Nd is None:
        Nd = getattr(getattr(doping, "inner", None), "Nd", sim_input.Nd)
    return float(Na or sim_input.Na), float(Nd or sim_input.Nd)
