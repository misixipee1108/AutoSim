"""Time-dependent study runner (PN transient or falling body)."""

from __future__ import annotations

from autosim.api.adapters.base import RunCallbacks
from autosim.plugins.engine.falling_engine import run_falling_multi, run_falling_single
from autosim.plugins.engine.pn_engine import run_pn_single
from autosim.plugins.studies._helpers import resolve_physics_instance
from autosim.project.schemas import SimulationProject, StudyDefinition


class TimeDependentStudyRunner:
    study_type = "time_dependent"

    def run(
        self,
        project: SimulationProject,
        study: StudyDefinition,
        callbacks: RunCallbacks | None = None,
    ):
        instance, sim_input = resolve_physics_instance(project, study)
        if instance.interface_id == "mechanics_0d_falling_body":
            iteration = study.parameters.get("iteration", {})
            max_trials = int(iteration.get("max_trials", 1)) if isinstance(iteration, dict) else 1
            if max_trials > 1:
                results = run_falling_multi(sim_input, callbacks=callbacks)
                return results[-1]
            return run_falling_single(sim_input, callbacks=callbacks)
        if sim_input.model_type != "transient_dd":
            sim_input = sim_input.model_copy(update={"model_type": "transient_dd"})
        sim_input = sim_input.model_copy(
            update={"transient": sim_input.transient.model_copy(update={"enabled": True})}
        )
        return run_pn_single(sim_input, callbacks=callbacks)
