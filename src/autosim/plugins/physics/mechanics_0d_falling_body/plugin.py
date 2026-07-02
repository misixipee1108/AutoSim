"""Mechanics 0D falling body physics plugin."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autosim.api.adapters.base import RunCallbacks
from autosim.plugins.engine.falling_engine import run_falling_single
from autosim.plugins.physics.mechanics_0d_falling_body.compat import project_to_falling_sim_input
from autosim.project.schemas import (
    ModelSection,
    PhysicsInterfaceDescriptor,
    PhysicsInterfaceInstance,
    ResultsSection,
    SimulationProject,
    StudyDefinition,
)
from autosim.schemas import SimInput, TrialResult

_MANIFEST = Path(__file__).resolve().parents[1] / "manifests" / "mechanics_0d_falling_body.json"


class Mechanics0DFallingBodyPlugin:
    interface_id = "mechanics_0d_falling_body"

    def get_descriptor(self) -> PhysicsInterfaceDescriptor:
        with open(_MANIFEST, encoding="utf-8") as f:
            data = json.load(f)
        return PhysicsInterfaceDescriptor.model_validate(data)

    def validate_instance(
        self,
        instance: PhysicsInterfaceInstance,
        model: ModelSection,
    ) -> None:
        if instance.interface_id != self.interface_id:
            raise ValueError(f"Expected {self.interface_id}, got {instance.interface_id}")
        settings = instance.settings
        if float(settings.get("mass", 0)) <= 0:
            raise ValueError("Mass must be positive")

    def build_sim_input(
        self,
        project: SimulationProject,
        study: StudyDefinition,
        instance: PhysicsInterfaceInstance,
    ) -> SimInput:
        self.validate_instance(instance, project.model)
        return project_to_falling_sim_input(project, study, instance)

    def run(
        self,
        sim_input: SimInput,
        callbacks: RunCallbacks | None = None,
        trial_index: int = 0,
    ) -> TrialResult:
        return run_falling_single(sim_input, callbacks=callbacks, trial_index=trial_index)

    def run_study(
        self,
        sim_input: SimInput,
        study: StudyDefinition,
        callbacks: RunCallbacks | None = None,
    ):
        from autosim.plugins.engine.falling_engine import run_falling_multi

        if sim_input.iteration.max_trials > 1 or study.study_type == "parameter_sweep":
            results = run_falling_multi(sim_input, callbacks=callbacks)
            return results[-1] if len(results) == 1 else results[-1]
        return run_falling_single(sim_input, callbacks=callbacks)

    def filter_outputs(
        self,
        raw_result: TrialResult,
        results: ResultsSection,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        ts = raw_result.trajectory
        xs = [p.t for p in ts] if ts else []
        profile_map = {
            "height": [p.y for p in ts],
            "velocity": [p.v for p in ts],
            "acceleration": [p.a for p in ts],
        }
        for var in results.output_variables:
            if var.kind == "profile" and var.var_id in profile_map:
                out[var.var_id] = {
                    "x": xs,
                    "y": profile_map[var.var_id],
                    "unit": var.unit,
                    "label": var.label,
                }
            elif var.kind == "scalar":
                scalar_map = {
                    "impact_time": raw_result.impact_time,
                    "impact_velocity": raw_result.impact_velocity,
                    "terminal_velocity": raw_result.terminal_velocity_estimate,
                }
                val = scalar_map.get(var.var_id)
                if val is not None:
                    out[var.var_id] = {"value": val, "unit": var.unit, "label": var.label}
        return out
