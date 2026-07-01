"""Solver registry."""

from __future__ import annotations

from autosim.pn.solvers.newton_damped import DampedNewtonSolver, NewtonLineSearchSolver, NewtonSolver

_SOLVERS = {
    "newton": NewtonSolver(),
    "damped_newton": DampedNewtonSolver(),
    "newton_line_search": NewtonLineSearchSolver(),
    "gummel": DampedNewtonSolver(),
}


def get_solver(method: str):
    if method == "gummel":
        return _SOLVERS["damped_newton"]
    return _SOLVERS.get(method, _SOLVERS["damped_newton"])


def list_solvers() -> list[str]:
    return list(_SOLVERS.keys())
