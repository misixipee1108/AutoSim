"""Convert legacy YAML configs to SimulationProject v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from autosim.plugins.physics.semiconductor_1d_poisson.compat import legacy_flat_to_project
from autosim.pn.schemas import PnRunConfig
from autosim.project.schemas import (
    ChartBindings,
    ChartTabMeta,
    OutputVariable,
    PhysicsInterfaceInstance,
    ResultsSection,
    SimulationProject,
    StudyDefinition,
    VisualizationRecipe,
)
from autosim.schemas import RunConfig


def _pn_results_for_study(study_type: str, instance_id: str) -> ResultsSection:
    base_profiles = [
        OutputVariable(
            var_id="potential",
            source=f"{instance_id}.psi",
            label="Potential ψ(x)",
            unit="V",
            kind="profile",
        ),
        OutputVariable(
            var_id="electric_field",
            source=f"{instance_id}.E",
            label="Electric Field E(x)",
            unit="V/cm",
            kind="profile",
        ),
        OutputVariable(
            var_id="Vbi",
            source="derived.Vbi",
            label="Built-in Potential",
            unit="V",
            kind="scalar",
        ),
    ]
    visualizations: list[VisualizationRecipe] = [
        VisualizationRecipe(
            viz_id="potential_profile",
            chart_type="line_profile",
            tab=ChartTabMeta(id="profiles", label="Profiles"),
            bindings=ChartBindings(x="x", y=["potential"], x_label="x (cm)", y_label="ψ (V)"),
        ),
    ]
    if study_type in ("bias_sweep", "stationary"):
        visualizations.append(
            VisualizationRecipe(
                viz_id="sweep_curves",
                chart_type="sweep",
                tab=ChartTabMeta(id="sweep", label="Sweep"),
                bindings=ChartBindings(
                    x="Vapp",
                    y=["W", "Cj", "Emax"],
                    x_label="Vapp (V)",
                    y_label="Value",
                ),
            )
        )
    if study_type == "cv_sweep":
        visualizations.append(
            VisualizationRecipe(
                viz_id="cv_curve",
                chart_type="sweep",
                tab=ChartTabMeta(id="sweep", label="C-V"),
                bindings=ChartBindings(x="Vapp", y=["Cj"], x_label="Vapp (V)", y_label="C (F/cm²)"),
            )
        )
    if study_type in ("bias_sweep",) and instance_id.startswith("pn_dd"):
        visualizations.append(
            VisualizationRecipe(
                viz_id="iv_curve",
                chart_type="sweep",
                tab=ChartTabMeta(id="iv", label="I-V"),
                bindings=ChartBindings(x="Vapp", y=["J"], x_label="Vapp (V)", y_label="J (A/cm²)"),
            )
        )
    if study_type == "time_dependent":
        visualizations = [
            VisualizationRecipe(
                viz_id="transient_profiles",
                chart_type="time_series",
                tab=ChartTabMeta(id="time_series", label="Transient"),
                bindings=ChartBindings(x="t", y=["potential"], x_label="t (s)", y_label="ψ (V)"),
            ),
        ]
    if study_type == "optimization":
        visualizations = [
            VisualizationRecipe(
                viz_id="optimization_history",
                chart_type="optimization",
                tab=ChartTabMeta(id="optimization", label="Optimization"),
                bindings=ChartBindings(x="trial", y=["objective"], x_label="Trial", y_label="Objective"),
            ),
        ]
    return ResultsSection(output_variables=base_profiles, visualizations=visualizations)


def _infer_pn_study_type(config: PnRunConfig) -> str:
    if config.optimization.enabled:
        return "optimization"
    if config.bias_scan.enabled:
        return "bias_sweep"
    if config.cv_scan.enabled:
        return "cv_sweep"
    if config.model_type == "transient_dd" or config.transient.enabled:
        return "time_dependent"
    if config.iteration.max_trials > 1:
        return "parameter_sweep"
    return "stationary"


def pn_config_to_project(
    config: PnRunConfig,
    *,
    project_id: str | None = None,
    title: str | None = None,
) -> SimulationProject:
    """Build SimulationProject from legacy PnRunConfig."""
    flat = config.model_dump(mode="json", exclude_none=True)
    project = legacy_flat_to_project(flat)
    if project_id:
        project = project.model_copy(update={"project_id": project_id})
    if title:
        project = project.model_copy(update={"title": title})

    study_type = _infer_pn_study_type(config)
    study = project.studies[0]
    study = study.model_copy(
        update={
            "study_type": study_type,
            "study_id": f"study_{study_type}",
            "label": study_type.replace("_", " ").title(),
            "parameters": {
                "Vapp": config.Vapp if config.Vapp is not None else 0.0,
                "bias_scan": config.bias_scan.model_dump(),
                "cv_scan": config.cv_scan.model_dump(),
                "transient": config.transient.model_dump(),
                "recombination": config.recombination.model_dump(),
                "breakdown": config.breakdown.model_dump(),
                "optimization": config.optimization.model_dump(),
                "iteration": config.iteration.model_dump(),
            },
        }
    )
    project = project.model_copy(update={"studies": [study], "active_study_id": study.study_id})

    iface = project.model.physics_interfaces[0]
    settings = dict(iface.settings)
    settings["model_type"] = config.model_type
    if config.doping:
        settings["doping"] = config.doping.model_dump()
    if config.recombination.enabled:
        settings["recombination"] = config.recombination.model_dump()
    settings["breakdown"] = config.breakdown.model_dump()

    interface_id = "semiconductor_1d_poisson"
    instance_id = "pn_poisson"
    if config.model_type in ("drift_diffusion", "transient_dd"):
        interface_id = "semiconductor_1d_dd"
        instance_id = "pn_dd"

    iface = iface.model_copy(
        update={
            "instance_id": instance_id,
            "interface_id": interface_id,
            "settings": settings,
        }
    )
    project = project.model_copy(
        update={
            "model": project.model.model_copy(
                update={"physics_interfaces": [iface]}
            ),
            "studies": [
                study.model_copy(update={"physics_interface_ids": [instance_id]})
            ],
            "results": _pn_results_for_study(study_type, instance_id),
        }
    )
    return project


def pn_yaml_to_project(path: str | Path, **kwargs: Any) -> SimulationProject:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    config = PnRunConfig.model_validate(data)
    stem = Path(path).stem
    return pn_config_to_project(
        config,
        project_id=f"{stem}_v2",
        title=stem.replace("_", " ").title(),
        **kwargs,
    )


def falling_config_to_project(
    config: RunConfig,
    *,
    project_id: str = "falling_body_v2",
    title: str = "Falling Body — Time Dependent",
) -> SimulationProject:
    from autosim.project.templates import falling_body_template

    project = falling_body_template()
    project = project.model_copy(update={"project_id": project_id, "title": title})
    iface = project.model.physics_interfaces[0]
    settings = {
        "mass": config.mass,
        "gravity": config.gravity,
        "y0": config.y0,
        "v0": config.v0,
        "ground_y": config.ground_y,
        "drag_model": config.drag_model.value,
        "drag_params": dict(config.drag_params),
        "t_max": config.t_max,
        "probe_interval": config.probe_interval,
        "dt": config.dt,
    }
    iface = iface.model_copy(update={"settings": settings})
    study = project.studies[0].model_copy(
        update={
            "parameters": {"iteration": config.iteration.model_dump()},
            "agent": project.studies[0].agent.model_copy(
                update={"backend": config.agent.backend.value}
            )
            if project.studies[0].agent
            else None,
        }
    )
    return project.model_copy(
        update={
            "model": project.model.model_copy(update={"physics_interfaces": [iface]}),
            "studies": [study],
        }
    )


def falling_yaml_to_project(path: str | Path) -> SimulationProject:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    config = RunConfig.model_validate(data)
    stem = Path(path).stem
    return falling_config_to_project(
        config,
        project_id=f"{stem}_v2",
        title=stem.replace("_", " ").title(),
    )
