"""Sparse linear system backends for Newton steps."""

from __future__ import annotations

import numpy as np
from scipy.sparse.linalg import bicgstab, spsolve


def solve_linear_system(J, rhs: np.ndarray, backend: str = "direct") -> np.ndarray:
    """Solve J @ x = rhs using direct or iterative (BiCGSTAB) backend."""
    if backend == "iterative":
        x, info = bicgstab(J, rhs, rtol=1e-8, atol=1e-12, maxiter=min(500, len(rhs) * 4))
        if info != 0:
            x = spsolve(J, rhs)
        return np.asarray(x)
    return np.asarray(spsolve(J, rhs))
