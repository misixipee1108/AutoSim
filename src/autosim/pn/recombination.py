"""Recombination models for drift-diffusion (SRH, Auger, radiative)."""

from __future__ import annotations

import numpy as np

from autosim.pn.schemas import RecombinationSpec


def srh_recombination(
    n: np.ndarray,
    p: np.ndarray,
    ni: float,
    tau_n: float,
    tau_p: float,
    n1: float,
    p1: float,
) -> np.ndarray:
    np_excess = n * p - ni**2
    denom = tau_p * (n + n1) + tau_n * (p + p1)
    denom = np.maximum(denom, 1e-30)
    return np_excess / denom


def auger_recombination(n: np.ndarray, p: np.ndarray, ni: float, Cn: float, Cp: float) -> np.ndarray:
    return (Cn * n + Cp * p) * (n * p - ni**2)


def radiative_recombination(n: np.ndarray, p: np.ndarray, ni: float, B: float) -> np.ndarray:
    return B * (n * p - ni**2)


def total_recombination(
    n: np.ndarray,
    p: np.ndarray,
    ni: float,
    spec: RecombinationSpec,
    *,
    B: float = 1.0e-15,
    Cn: float = 2.8e-31,
    Cp: float = 9.9e-32,
) -> tuple[np.ndarray, dict[str, float]]:
    if not spec.enabled:
        zeros = np.zeros_like(n)
        return zeros, {"R_max": 0.0, "R_srh": 0.0, "R_auger": 0.0, "R_rad": 0.0}
    r_srh = srh_recombination(n, p, ni, spec.tau_n, spec.tau_p, spec.n1, spec.p1) if spec.srh else 0.0
    r_aug = auger_recombination(n, p, ni, Cn, Cp) if spec.auger else 0.0
    r_rad = radiative_recombination(n, p, ni, B) if spec.radiative else 0.0
    r_total = np.asarray(r_srh, dtype=float) + np.asarray(r_aug, dtype=float) + np.asarray(r_rad, dtype=float)
    stats = {
        "R_max": float(np.max(np.abs(r_total))),
        "R_srh": float(np.max(np.abs(r_srh))) if spec.srh else 0.0,
        "R_auger": float(np.max(np.abs(r_aug))) if spec.auger else 0.0,
        "R_rad": float(np.max(np.abs(r_rad))) if spec.radiative else 0.0,
    }
    return r_total, stats
