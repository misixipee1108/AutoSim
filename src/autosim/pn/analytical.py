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


def bernoulli_b(x: np.ndarray | float) -> np.ndarray | float:
    """Bernoulli function B(x) = x / (exp(x) - 1); stable near x=0."""
    x_arr = np.asarray(x, dtype=float)
    out = np.ones_like(x_arr)
    mask = np.abs(x_arr) > 1e-8
    xm = x_arr[mask]
    out[mask] = xm / np.expm1(xm)
    out[~mask & (x_arr < 0)] = 1.0 + 0.5 * x_arr[~mask & (x_arr < 0)]
    return float(out) if np.isscalar(x) or out.ndim == 0 else out


def shockley_saturation_current(
    Na: float,
    Nd: float,
    material: MaterialSpec,
    Lp: float,
    Ln: float,
) -> float:
    """Diffusion-limited saturation current density (A/cm^2).

    Js = q * ni^2 * (D_n/(Na*Lp) + D_p/(Nd*Ln)), D = mu * Vt.
    Sze & Ng (2012) Ch. 2.
    """
    Vt = material.Vt
    q = material.q
    ni = material.ni
    Dn = material.mu_n * Vt
    Dp = material.mu_p * Vt
    return q * ni**2 * (Dn / (Na * Lp) + Dp / (Nd * Ln))


def shockley_current(Vapp: float, Js: float, material: MaterialSpec, ideality: float = 1.0) -> float:
    """Shockley diode I-V: J = Js * (exp(V / (n*Vt)) - 1)."""
    Vt = material.Vt
    n = max(ideality, 0.5)
    return Js * (math.exp(Vapp / (n * Vt)) - 1.0)


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
