"""1D spatial mesh generation."""

from __future__ import annotations

import numpy as np


def uniform_mesh(Lp: float, Ln: float, Nx: int) -> tuple[np.ndarray, np.ndarray]:
    """Uniform grid on [-Lp, Ln] with Nx points. Returns x and dx array."""
    x = np.linspace(-Lp, Ln, Nx)
    dx = np.diff(x)
    return x, dx


def build_mesh(
    Lp: float,
    Ln: float,
    Nx: int,
    *,
    junction_refinement: bool = False,
    refinement_ratio: float = 3.0,
    width_frac: float = 0.1,
) -> tuple[np.ndarray, np.ndarray]:
    """Build 1D mesh, optionally with junction refinement near x=0."""
    if not junction_refinement or Nx < 20:
        return uniform_mesh(Lp, Ln, Nx)
    return junction_refined_mesh(Lp, Ln, Nx, refinement_ratio, width_frac)


def junction_refined_mesh(
    Lp: float,
    Ln: float,
    Nx: int,
    refinement_ratio: float = 3.0,
    width_frac: float = 0.1,
) -> tuple[np.ndarray, np.ndarray]:
    """Geometrically refined mesh near the junction at x=0."""
    ratio = max(refinement_ratio, 1.1)
    w_p = Lp * width_frac
    w_n = Ln * width_frac
    n_junc = max(Nx // 5, 8)
    n_bulk = Nx - n_junc
    n_p = max(n_bulk // 2, 4)
    n_n = max(n_bulk - n_p, 4)

    def _tanh_cluster(start: float, end: float, n: int, dense_at: float) -> np.ndarray:
        if n <= 1:
            return np.array([start])
        t = np.linspace(-1.0, 1.0, n)
        scale = max(abs(end - start), 1e-20)
        if dense_at > start:
            u = np.tanh(2.5 * t)
            u = (u - u[0]) / max(u[-1] - u[0], 1e-20)
            seg = start + u * (dense_at - start)
        else:
            u = np.tanh(2.5 * t)
            u = (u - u[0]) / max(u[-1] - u[0], 1e-20)
            seg = dense_at + u * (end - dense_at)
        return seg

    x_p_far = _tanh_cluster(-Lp, -w_p, n_p, -w_p)
    x_p_junc = _tanh_cluster(-w_p, 0.0, n_junc // 2 + 1, 0.0)
    x_n_junc = _tanh_cluster(0.0, w_n, n_junc // 2 + 1, 0.0)
    x_n_far = _tanh_cluster(w_n, Ln, n_n, w_n)

    x = np.unique(np.concatenate([x_p_far, x_p_junc, x_n_junc, x_n_far]))
    if len(x) < Nx:
        extra = np.linspace(-Lp, Ln, Nx)
        x = np.unique(np.concatenate([x, extra]))
    if len(x) > Nx:
        idx = np.linspace(0, len(x) - 1, Nx, dtype=int)
        x = x[idx]
    x = np.sort(x)
    dx = np.diff(x)
    return x, dx
