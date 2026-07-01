"""PN optimization tests."""

from autosim.orchestrator.pn_optimizer import run_pn_optimization
from autosim.pn.schemas import (
    PnDesignVarSpec,
    PnObjectiveSpec,
    PnOptimizationSpec,
    PnSimInput,
)


def test_random_optimization_finds_feasible_trial():
    sim_input = PnSimInput(
        Na=1e18,
        Nd=1e16,
        Nx=100,
        tol=1e-3,
        max_iter=100,
        optimization=PnOptimizationSpec(
            enabled=True,
            method="random",
            max_trials=5,
            design_vars=[
                PnDesignVarSpec(name="Nd", min=5e15, max=5e16),
            ],
            objectives=[
                PnObjectiveSpec(name="Emax", target="min", constraint="< 5e5 V/cm"),
            ],
        ),
    )
    results, best = run_pn_optimization(sim_input)
    assert len(results) == 5
    assert best is not None
    assert best.converged
