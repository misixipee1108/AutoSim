"""C-V sweep study runner."""

from __future__ import annotations

from autosim.api.adapters.base import RunCallbacks
from autosim.plugins.engine.pn_engine import run_pn_single
from autosim.plugins.studies._helpers import resolve_physics_instance
from autosim.project.schemas import SimulationProject, StudyDefinition


class CvSweepStudyRunner:
    study_type = "cv_sweep"

    def run(
        self,
        project: SimulationProject,
        study: StudyDefinition,
        callbacks: RunCallbacks | None = None,
    ):
        _, sim_input = resolve_physics_instance(project, study)
        sim_input = sim_input.model_copy(
            update={"cv_scan": sim_input.cv_scan.model_copy(update={"enabled": True})}
        )
        return run_pn_single(sim_input, callbacks=callbacks)
