"""Breakdown and impact-ionization models (lightweight, non-full-avalanche)."""

from __future__ import annotations

import math

import numpy as np

from autosim.pn.schemas import BreakdownSpec


def chynoweth_alpha(E: np.ndarray, a: float, b: float) -> np.ndarray:
    """Chynoweth-type alpha(E) in cm^-1; E in V/cm."""
    Eabs = np.abs(E)
    return a * np.exp(-b / np.maximum(Eabs, 1.0))


def impact_ionization_multiplier(E: np.ndarray, x: np.ndarray, spec: BreakdownSpec) -> float:
    """Integrate alpha along x to estimate multiplication factor M = exp(int alpha dx)."""
    if spec.alpha_model == "none" or len(x) < 2:
        return 1.0
    alpha = chynoweth_alpha(E, spec.alpha_n, spec.alpha_exp)
    dx = np.diff(x)
    alpha_mid = 0.5 * (alpha[:-1] + alpha[1:])
    integral = float(np.sum(alpha_mid * dx))
    return math.exp(min(integral, 50.0))


def breakdown_assessment(
    E: np.ndarray,
    x: np.ndarray,
    spec: BreakdownSpec,
    J_base: float | None = None,
) -> dict[str, float | bool]:
    emax = float(np.max(np.abs(E))) if len(E) else 0.0
    risk = emax > spec.E_crit
    M = impact_ionization_multiplier(E, x, spec)
    J_mult = (J_base or 0.0) * M
    score = min(emax / max(spec.E_crit, 1.0), 10.0) / 10.0
    return {
        "Emax": emax,
        "breakdown_risk": risk,
        "M_ionization": M,
        "J_mult": J_mult,
        "breakdown_risk_score": score,
    }
