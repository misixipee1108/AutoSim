"""Parameter sweep / multi-trial iteration study runner."""

from __future__ import annotations

from autosim.api.adapters.base import RunCallbacks
from autosim.plugins.engine.falling_engine import run_falling_multi
from autosim.plugins.engine.pn_engine import run_pn_multi
from autosim.plugins.studies._helpers import resolve_physics_instance
from autosim.project.schemas import SimulationProject, StudyDefinition


class ParameterSweepStudyRunner:
    study_type = "parameter_sweep"

    def run(
        self,
        project: SimulationProject,
        study: StudyDefinition,
        callbacks: RunCallbacks | None = None,
    ):
        instance, sim_input = resolve_physics_instance(project, study)
        if instance.interface_id == "mechanics_0d_falling_body":
            results = run_falling_multi(sim_input, callbacks=callbacks)
            return results
        results = run_pn_multi(sim_input, callbacks=callbacks)
        return results
