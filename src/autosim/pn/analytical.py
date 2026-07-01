"""Analytical depletion-approximation formulas for validation."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from autosim.pn.materials import MaterialSpec


@dataclass(frozen=True)
class DepletionAnalytic:
    Vbi: float
    W: float
    Wp: float
    Wn: float
    Emax: float


def built_in_potential(Na: float, Nd: float, material: MaterialSpec) -> float:
    """Vbi = Vt * ln(Na*Nd / ni^2)."""
    Vt = material.Vt
    return Vt * math.log(Na * Nd / material.ni**2)


def depletion_width(
    Na: float,
    Nd: float,
    material: MaterialSpec,
    Vapp: float = 0.0,
) -> DepletionAnalytic:
    """Abrupt junction depletion approximation (Sze Ch. 2).

    Vapp > 0 reduces effective barrier (forward bias convention).
    """
    Vbi = built_in_potential(Na, Nd, material)
    Veff = max(Vbi - Vapp, 0.0)
    eps = material.eps
    q = material.q

    W = math.sqrt(2 * eps / q * (1.0 / Na + 1.0 / Nd) * Veff)
    Wp = W * Nd / (Na + Nd)
    Wn = W * Na / (Na + Nd)
    Emax = 2 * Veff / W if W > 0 else 0.0

    return DepletionAnalytic(Vbi=Vbi, W=W, Wp=Wp, Wn=Wn, Emax=Emax)


def contact_potentials(
    Na: float,
    Nd: float,
    material: MaterialSpec,
    Vapp: float = 0.0,
) -> tuple[float, float]:
    """Dirichlet BC at P and N contacts.

    P side (x=-Lp): psi_p = -Vt*ln(Na/ni) - Vapp/2
    N side (x=+Ln): psi_n = +Vt*ln(Nd/ni) + Vapp/2
    """
    Vt = material.Vt
    ni = material.ni
    psi_p = -Vt * math.log(Na / ni) - Vapp / 2.0
    psi_n = Vt * math.log(Nd / ni) + Vapp / 2.0
    return psi_p, psi_n


def depletion_psi_profile(
    x: np.ndarray,
    Na: float,
    Nd: float,
    material: MaterialSpec,
    Vapp: float = 0.0,
) -> np.ndarray:
    """Piecewise parabolic depletion-approximation potential for initial guess."""
    dep = depletion_width(Na, Nd, material, Vapp)
    Wp, Wn = dep.Wp, dep.Wn
    psi_p, psi_n = contact_potentials(Na, Nd, material, Vapp)
    eps = material.eps
    q = material.q

    psi = np.zeros_like(x, dtype=float)
    for i, xi in enumerate(x):
        if xi <= -Wp:
            psi[i] = psi_p
        elif xi < 0:
            psi[i] = psi_p + (q * Na / (2 * eps)) * (xi + Wp) ** 2
        elif xi <= Wn:
            psi[i] = psi_n - (q * Nd / (2 * eps)) * (Wn - xi) ** 2
        else:
            psi[i] = psi_n
    return psi
