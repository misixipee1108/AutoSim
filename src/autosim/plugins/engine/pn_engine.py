"""Internal PN execution helpers for study runners (not public API)."""

from __future__ import annotations

from typing import Any

from autosim.api.adapters.base import RunCallbacks
from autosim.api.adapters.pn import PnAdapter
from autosim.pn.schemas import PnRunConfig, PnSimInput, PnTrialResult


def sim_input_to_config(sim_input: PnSimInput) -> PnRunConfig:
    return PnRunConfig.model_validate(sim_input.model_dump())


def run_pn_single(
    sim_input: PnSimInput,
    callbacks: RunCallbacks | None = None,
    trial_index: int = 0,
) -> PnTrialResult:
    config = sim_input_to_config(sim_input)
    return PnAdapter().run_trial(config, trial_index=trial_index, callbacks=callbacks)


def run_pn_multi(
    sim_input: PnSimInput,
    callbacks: RunCallbacks | None = None,
) -> list[PnTrialResult]:
    config = sim_input_to_config(sim_input)
    return PnAdapter().run_iteration(config, callbacks=callbacks)


def run_pn_study(
    sim_input: PnSimInput,
    study_type: str,
    callbacks: RunCallbacks | None = None,
) -> PnTrialResult | list[PnTrialResult]:
    if study_type in ("stationary", "time_dependent", "cv_sweep"):
        return run_pn_single(sim_input, callbacks=callbacks)
    if study_type in ("bias_sweep", "optimization", "parameter_sweep"):
        return run_pn_multi(sim_input, callbacks=callbacks)
    return run_pn_single(sim_input, callbacks=callbacks)
