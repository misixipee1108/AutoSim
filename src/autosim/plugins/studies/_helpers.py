"""Shared helpers for study runners."""

from __future__ import annotations

from autosim.api.adapters.base import RunCallbacks
from autosim.plugins.registry import get_physics_plugin
from autosim.project.schemas import PhysicsInterfaceInstance, SimulationProject, StudyDefinition


def resolve_physics_instance(
    project: SimulationProject,
    study: StudyDefinition,
) -> tuple[PhysicsInterfaceInstance, object]:
    if not study.physics_interface_ids:
        raise ValueError("Study has no physics_interface_ids")
    instance_id = study.physics_interface_ids[0]
    instance = next(
        (i for i in project.model.physics_interfaces if i.instance_id == instance_id),
        None,
    )
    if instance is None:
        raise KeyError(f"Physics interface instance not found: {instance_id}")
    plugin = get_physics_plugin(instance.interface_id)
    plugin.validate_instance(instance, project.model)
    sim_input = plugin.build_sim_input(project, study, instance)
    return instance, sim_input


def run_physics_study(
    project: SimulationProject,
    study: StudyDefinition,
    callbacks: RunCallbacks | None = None,
):
    instance, sim_input = resolve_physics_instance(project, study)
    plugin = get_physics_plugin(instance.interface_id)
    if hasattr(plugin, "run_study"):
        return plugin.run_study(sim_input, study, callbacks=callbacks)
    return plugin.run(sim_input, callbacks=callbacks, trial_index=0)
