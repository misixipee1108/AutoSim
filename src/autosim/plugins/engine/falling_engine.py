"""Internal falling-body execution helpers."""

from __future__ import annotations

from autosim.api.adapters.base import RunCallbacks
from autosim.api.adapters.falling_block import FallingBlockAdapter
from autosim.schemas import RunConfig, SimInput, TrialResult


def sim_input_to_config(sim_input: SimInput) -> RunConfig:
    return RunConfig.model_validate(sim_input.model_dump())


def run_falling_single(
    sim_input: SimInput,
    callbacks: RunCallbacks | None = None,
    trial_index: int = 0,
) -> TrialResult:
    config = sim_input_to_config(sim_input)
    return FallingBlockAdapter().run_trial(config, trial_index=trial_index, callbacks=callbacks)


def run_falling_multi(
    sim_input: SimInput,
    callbacks: RunCallbacks | None = None,
) -> list[TrialResult]:
    config = sim_input_to_config(sim_input)
    return FallingBlockAdapter().run_iteration(config, callbacks=callbacks)
