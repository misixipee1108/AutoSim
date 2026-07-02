"""Map SimulationProject v2 to falling-body SimInput."""

from __future__ import annotations

from typing import Any

from autosim.project.schemas import PhysicsInterfaceInstance, SimulationProject, StudyDefinition
from autosim.schemas import AgentBackend, AgentConfig, DragModelType, IterationConfig, SimInput


def project_to_falling_sim_input(
    project: SimulationProject,
    study: StudyDefinition,
    instance: PhysicsInterfaceInstance,
) -> SimInput:
    settings = dict(instance.settings)
    iteration_raw = study.parameters.get("iteration", {})
    iteration = (
        IterationConfig.model_validate(iteration_raw)
        if isinstance(iteration_raw, dict)
        else IterationConfig(max_trials=1)
    )
    agent = AgentConfig()
    if study.agent:
        agent = AgentConfig(
            backend=AgentBackend(study.agent.backend),
            probe_window=study.agent.probe_window,
        )
    drag_model = settings.get("drag_model", "quadratic")
    if isinstance(drag_model, str):
        drag_model = DragModelType(drag_model)
    return SimInput(
        mass=float(settings.get("mass", 1.0)),
        gravity=float(settings.get("gravity", 9.81)),
        y0=float(settings.get("y0", 100.0)),
        v0=float(settings.get("v0", 0.0)),
        ground_y=float(settings.get("ground_y", 0.0)),
        drag_model=drag_model,
        drag_params=dict(settings.get("drag_params", {})),
        t_max=float(settings.get("t_max", 30.0)),
        probe_interval=float(settings.get("probe_interval", 0.1)),
        dt=float(settings.get("dt", 0.01)),
        agent=agent,
        iteration=iteration,
    )
