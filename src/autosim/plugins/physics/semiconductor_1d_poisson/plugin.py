"""Semiconductor 1D Poisson physics interface plugin."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autosim.api.adapters.base import RunCallbacks
from autosim.plugins.physics.semiconductor_1d_poisson.compat import project_to_pn_sim_input
from autosim.pn.schemas import PnTrialResult
from autosim.project.schemas import (
    ModelSection,
    PhysicsInterfaceDescriptor,
    PhysicsInterfaceInstance,
    ResultsSection,
    SimulationProject,
    StudyDefinition,
)

_MANIFEST = Path(__file__).resolve().parents[1] / "manifests" / "semiconductor_1d_poisson.json"


class Semiconductor1DPoissonPlugin:
    interface_id = "semiconductor_1d_poisson"

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
        doping = instance.settings.get("doping", {})
        if isinstance(doping, dict):
            na = doping.get("Na") or instance.settings.get("Na")
            nd = doping.get("Nd") or instance.settings.get("Nd")
            if na is None or nd is None:
                raise ValueError("Doping Na and Nd are required for abrupt PN junction")
        if not model.mesh.Nx or model.mesh.Nx < 2:
            raise ValueError("Mesh Nx must be >= 2")

    def build_sim_input(
        self,
        project: SimulationProject,
        study: StudyDefinition,
        instance: PhysicsInterfaceInstance,
    ) -> Any:
        self.validate_instance(instance, project.model)
        return project_to_pn_sim_input(project, study, instance)

    def run(
        self,
        sim_input: Any,
        callbacks: RunCallbacks | None = None,
        trial_index: int = 0,
    ) -> PnTrialResult:
        from autosim.api.adapters.pn import PnAdapter
        from autosim.pn.schemas import PnRunConfig

        config = PnRunConfig.model_validate(sim_input.model_dump())
        return PnAdapter().run_trial(config, trial_index=trial_index, callbacks=callbacks)

    def filter_outputs(
        self,
        raw_result: PnTrialResult,
        results: ResultsSection,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        xs = [p.x for p in raw_result.profile] if raw_result.profile else []
        profile_map = {
            "potential": [p.psi for p in raw_result.profile],
            "electric_field": [p.E for p in raw_result.profile],
            "electron_density": [p.n for p in raw_result.profile],
            "hole_density": [p.p for p in raw_result.profile],
            "charge_density": [p.rho for p in raw_result.profile],
        }
        for var in results.output_variables:
            if var.kind == "profile":
                key = var.var_id
                if key in profile_map:
                    out[key] = {"x": xs, "y": profile_map[key], "unit": var.unit, "label": var.label}
            elif var.kind == "scalar":
                scalar_map = {
                    "Vbi": raw_result.Vbi_numeric,
                    "W": raw_result.W_numeric,
                    "Emax": raw_result.Emax_numeric,
                    "Cj": raw_result.Cj_estimate,
                }
                val = scalar_map.get(var.var_id)
                if val is not None:
                    out[var.var_id] = {"value": val, "unit": var.unit, "label": var.label}
        return out
