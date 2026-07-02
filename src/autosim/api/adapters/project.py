"""Project-based simulation adapter (SimulationProject v2 — sole public entry)."""

from __future__ import annotations

from typing import Any

from autosim.api.adapters.base import RunCallbacks
from autosim.api.adapters.falling_block import FallingBlockAdapter
from autosim.api.adapters.pn import PnAdapter
from autosim.api.schemas import RunStatus, TrialSummary, UnifiedRunResult
from autosim.plugins.registry import get_physics_plugin, get_study_runner
from autosim.pn.schemas import PnTrialResult
from autosim.project.schemas import SimulationProject, StudyDefinition
from autosim.schemas import TrialResult


class ProjectAdapter:
    model_id = "simulation_project_v2"

    def validate_project(self, raw: dict[str, Any]) -> SimulationProject:
        return SimulationProject.model_validate(raw)

    def get_active_study(self, project: SimulationProject) -> StudyDefinition:
        study_id = project.active_study_id
        if not study_id and project.studies:
            return project.studies[0]
        for study in project.studies:
            if study.study_id == study_id:
                return study
        raise KeyError(f"Active study not found: {study_id}")

    def _physics_category(self, project: SimulationProject) -> str:
        study = self.get_active_study(project)
        if not study.physics_interface_ids:
            return "semiconductor"
        instance_id = study.physics_interface_ids[0]
        instance = next(
            (i for i in project.model.physics_interfaces if i.instance_id == instance_id),
            None,
        )
        if instance is None:
            return "semiconductor"
        if instance.interface_id == "mechanics_0d_falling_body":
            return "mechanics"
        return "semiconductor"

    def run_study(
        self,
        project: SimulationProject,
        study: StudyDefinition | None = None,
        callbacks: RunCallbacks | None = None,
        max_trials: int = 1,
    ) -> Any:
        study = study or self.get_active_study(project)
        if max_trials > 1 and study.study_type == "stationary":
            study = study.model_copy(
                update={
                    "study_type": "parameter_sweep",
                    "parameters": {
                        **study.parameters,
                        "iteration": {
                            **(study.parameters.get("iteration") or {}),
                            "max_trials": max_trials,
                        },
                    },
                }
            )
        runner = get_study_runner(study.study_type)
        return runner.run(project, study, callbacks=callbacks)

    def normalize_result(
        self,
        run_id: str,
        project: SimulationProject,
        raw: Any,
        logs: list[str] | None = None,
        all_trials: list[Any] | None = None,
    ) -> UnifiedRunResult:
        category = self._physics_category(project)
        if category == "mechanics":
            fb = FallingBlockAdapter()
            if isinstance(raw, list):
                last = raw[-1]
                unified = fb.normalize_result(run_id, last, logs=logs, all_trials=raw)
            else:
                unified = fb.normalize_result(run_id, raw, logs=logs)
        else:
            pn = PnAdapter()
            if isinstance(raw, list):
                last = raw[-1]
                unified = pn.normalize_result(run_id, last, logs=logs, all_trials=raw)
            elif all_trials:
                unified = pn.normalize_result(run_id, raw, logs=logs, all_trials=all_trials)
            else:
                unified = pn.normalize_result(run_id, raw, logs=logs)

        unified.model_id = project.project_id
        self._apply_plugin_filters(unified, project, raw if not isinstance(raw, list) else raw[-1])
        return unified

    def _apply_plugin_filters(
        self,
        unified: UnifiedRunResult,
        project: SimulationProject,
        raw: PnTrialResult | TrialResult,
    ) -> None:
        study = self.get_active_study(project)
        if not study.physics_interface_ids:
            return
        instance_id = study.physics_interface_ids[0]
        instance = next(
            (i for i in project.model.physics_interfaces if i.instance_id == instance_id),
            None,
        )
        if instance is None:
            return
        plugin = get_physics_plugin(instance.interface_id)
        filtered = plugin.filter_outputs(raw, project.results)

        # Keep all solver profiles in the API payload; the frontend viz catalog
        # selects which series to display. Do not strip profiles using legacy
        # visualization recipe bindings.y (that list only describes default charts).

        from autosim.api.schemas import ScalarMetric

        for var_id, data in filtered.items():
            if var_id in unified.scalars:
                continue
            if isinstance(data, dict) and "value" in data:
                unified.scalars[var_id] = ScalarMetric(
                    value=float(data["value"]),
                    unit=data.get("unit", ""),
                    label=data.get("label", var_id),
                )

    def normalize_trials(
        self,
        run_id: str,
        project: SimulationProject,
        results: list[Any],
        logs: list[str] | None = None,
    ) -> UnifiedRunResult:
        unified = self.normalize_result(run_id, project, results[-1], logs=logs, all_trials=results)
        category = self._physics_category(project)
        if category == "mechanics":
            adapter = FallingBlockAdapter()
        else:
            adapter = PnAdapter()
        unified.trials = [
            TrialSummary(
                trial_index=r.trial_index,
                status=RunStatus.COMPLETED if not r.early_stopped else RunStatus.EARLY_STOPPED,
                stop_reason=r.stop_reason,
                early_stopped=r.early_stopped,
                scalars=adapter.normalize_result(run_id, r).scalars,
            )
            for r in results
        ]
        return unified
