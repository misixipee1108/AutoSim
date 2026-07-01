"""1D PN junction simulation."""

from autosim.pn.solve import solve_pn
from autosim.pn.poisson_solver import solve_pn_poisson
from autosim.pn.depletion_solver import solve_pn_depletion

__all__ = ["solve_pn", "solve_pn_poisson", "solve_pn_depletion"]
