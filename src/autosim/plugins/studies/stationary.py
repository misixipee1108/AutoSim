"""Stationary study runner."""

from __future__ import annotations

from autosim.api.adapters.base import RunCallbacks
from autosim.plugins.studies._helpers import run_physics_study
from autosim.project.schemas import SimulationProject, StudyDefinition


class StationaryStudyRunner:
    study_type = "stationary"

    def run(
        self,
        project: SimulationProject,
        study: StudyDefinition,
        callbacks: RunCallbacks | None = None,
    ):
        return run_physics_study(project, study, callbacks=callbacks)
