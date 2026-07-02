"""Optimization study runner."""

from __future__ import annotations

from autosim.api.adapters.base import RunCallbacks
from autosim.plugins.engine.pn_engine import run_pn_multi
from autosim.plugins.studies._helpers import resolve_physics_instance
from autosim.project.schemas import SimulationProject, StudyDefinition


class OptimizationStudyRunner:
    study_type = "optimization"

    def run(
        self,
        project: SimulationProject,
        study: StudyDefinition,
        callbacks: RunCallbacks | None = None,
    ):
        _, sim_input = resolve_physics_instance(project, study)
        sim_input = sim_input.model_copy(
            update={"optimization": sim_input.optimization.model_copy(update={"enabled": True})}
        )
        results = run_pn_multi(sim_input, callbacks=callbacks)
        return results[-1]
