"""Nonlinear solver protocol."""

from __future__ import annotations

from typing import Callable, Protocol

import numpy as np

from autosim.pn.convergence import ConvergenceContext, ConvergenceSpec
from autosim.pn.schemas import PnNewtonProbe


class NonlinearSolver(Protocol):
    name: str

    def solve(
        self,
        psi0: np.ndarray,
        residual_fn: Callable[[np.ndarray], tuple[np.ndarray, object, dict]],
        tol: float,
        max_iter: int,
        damping: float,
        on_probe: Callable[[PnNewtonProbe], object] | None,
        mesh_quality: float,
        adaptive_damping: bool = False,
        conv_ctx: ConvergenceContext | None = None,
        conv_spec: ConvergenceSpec | None = None,
    ) -> tuple[np.ndarray, list[PnNewtonProbe], bool, str]:
        ...
