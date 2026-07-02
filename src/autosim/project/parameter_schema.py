"""Parameter schemas for project tree nodes (geometry, mesh, materials, studies)."""

from __future__ import annotations

from autosim.api.schemas import ParameterSchema
from autosim.plugins.registry import get_physics_descriptor, list_physics_descriptors
from autosim.project.physics_tree import parse_physics_interface_tree_path
from autosim.project.schemas import SimulationProject


def parameters_for_tree_path(project: SimulationProject, tree_path: str) -> list[ParameterSchema]:
    """Resolve parameter schemas for a selected model-tree node path."""
    if tree_path == "model.geometry":
        return [
            ParameterSchema(
                name="model.geometry.junction_position",
                label="Junction Position",
                type="number",
                unit="cm",
                default=project.model.geometry.junction_position,
                group="Geometry",
            ),
            ParameterSchema(
                name="model.geometry.segments.0.length",
                label="P-side Length",
                type="number",
                unit="cm",
                default=_segment_length(project, "p"),
                group="Geometry",
            ),
            ParameterSchema(
                name="model.geometry.segments.1.length",
                label="N-side Length",
                type="number",
                unit="cm",
                default=_segment_length(project, "n"),
                group="Geometry",
            ),
        ]
    if tree_path == "model.mesh":
        mesh = project.model.mesh
        jref = mesh.junction_refinement
        return [
            ParameterSchema(
                name="model.mesh.Nx",
                label="Grid Points",
                type="integer",
                default=mesh.Nx,
                min=20,
                max=5000,
                group="Mesh",
            ),
            ParameterSchema(
                name="model.mesh.junction_refinement.enabled",
                label="Junction Refinement",
                type="boolean",
                default=jref.enabled,
                group="Mesh",
            ),
            ParameterSchema(
                name="model.mesh.junction_refinement.ratio",
                label="Refinement Ratio",
                type="number",
                default=jref.ratio,
                min=1.1,
                max=10.0,
                group="Mesh",
            ),
            ParameterSchema(
                name="model.mesh.junction_refinement.width_frac",
                label="Junction Zone Fraction",
                type="number",
                default=jref.width_frac,
                min=0.01,
                max=0.5,
                group="Mesh",
            ),
        ]
    if tree_path == "model.material":
        mat = project.model.materials[0] if project.model.materials else None
        return [
            ParameterSchema(
                name="model.materials.0.material_id",
                label="Material",
                type="select",
                default=mat.material_id if mat else "Si",
                group="Material",
                options=[
                    {"value": "Si", "label": "Silicon (Si)"},
                    {"value": "Ge", "label": "Germanium (Ge)"},
                    {"value": "GaAs", "label": "GaAs"},
                ],
            ),
            ParameterSchema(
                name="model.materials.0.temperature_k",
                label="Temperature",
                type="number",
                unit="K",
                default=mat.temperature_k if mat else 300.0,
                min=100,
                max=500,
                group="Material",
            ),
        ]
    if tree_path.startswith("model.physics_interfaces."):
        instance_id, group_name = parse_physics_interface_tree_path(tree_path)
        if not instance_id:
            return []
        instance = next(
            (i for i in project.model.physics_interfaces if i.instance_id == instance_id),
            None,
        )
        if instance:
            desc = get_physics_descriptor(instance.interface_id)
            prefix = f"model.physics_interfaces.{instance_id}.settings"
            params: list[ParameterSchema] = []
            for p in desc.parameter_schema:
                if group_name and p.group != group_name:
                    continue
                name = p.name
                if name.startswith("settings."):
                    name = f"model.physics_interfaces.{instance_id}.{name}"
                elif not name.startswith("model."):
                    name = f"{prefix}.{name}"
                params.append(p.model_copy(update={"name": name}))
            return params
        return []

    if ".study_params" in tree_path:
        study_id = tree_path.split(".")[1]
        study = next((s for s in project.studies if s.study_id == study_id), None)
        if study:
            return [
                ParameterSchema(
                    name=f"studies.{study_id}.parameters.Vapp",
                    label="Applied Bias",
                    type="number",
                    unit="V",
                    default=float(study.parameters.get("Vapp", 0.0)),
                    min=-5,
                    max=5,
                    group="Study",
                ),
            ]

    if ".solver_sequence" in tree_path:
        study_id = tree_path.split(".")[1]
        study = next((s for s in project.studies if s.study_id == study_id), None)
        if study and study.solver_sequence:
            step = study.solver_sequence[0]
            settings = step.settings
            conv = settings.convergence
            prefix = f"studies.{study_id}.solver_sequence.0.settings"
            return [
                ParameterSchema(
                    name=f"{prefix}.relative_tol",
                    label="Relative Tolerance",
                    type="number",
                    default=settings.relative_tol,
                    min=1e-10,
                    max=1e-2,
                    group="Solver",
                ),
                ParameterSchema(
                    name=f"{prefix}.max_iter",
                    label="Max Iterations",
                    type="integer",
                    default=settings.max_iter,
                    min=10,
                    max=1000,
                    group="Solver",
                ),
                ParameterSchema(
                    name=f"{prefix}.damping",
                    label="Damping Factor",
                    type="number",
                    default=settings.damping,
                    min=0.01,
                    max=1.0,
                    group="Solver",
                ),
                ParameterSchema(
                    name=f"studies.{study_id}.solver_sequence.0.solver_id",
                    label="Nonlinear Solver",
                    type="select",
                    default=step.solver_id,
                    group="Solver",
                    options=[
                        {"value": "newton", "label": "Newton"},
                        {"value": "damped_newton", "label": "Damped Newton"},
                        {"value": "newton_line_search", "label": "Newton + Line Search"},
                    ],
                ),
                ParameterSchema(
                    name=f"{prefix}.convergence.criterion",
                    label="Convergence Criterion",
                    type="select",
                    default=conv.criterion,
                    group="Solver",
                    options=[
                        {"value": "residual", "label": "Residual only"},
                        {"value": "solution", "label": "Solution step only"},
                        {"value": "either", "label": "Either"},
                        {"value": "both", "label": "Both (COMSOL-style)"},
                    ],
                ),
            ]

    if ".agent" in tree_path:
        study_id = tree_path.split(".")[1]
        study = next((s for s in project.studies if s.study_id == study_id), None)
        agent = study.agent if study else None
        return [
            ParameterSchema(
                name=f"studies.{study_id}.agent.backend",
                label="Agent Backend",
                type="select",
                default=agent.backend if agent else "rules",
                group="Agent",
                options=[
                    {"value": "rules", "label": "Rules Only"},
                    {"value": "deepseek", "label": "DeepSeek LLM"},
                    {"value": "hybrid", "label": "Hybrid"},
                ],
            ),
            ParameterSchema(
                name=f"studies.{study_id}.agent.probe_window",
                label="Probe Window",
                type="integer",
                default=agent.probe_window if agent else 10,
                min=1,
                max=100,
                group="Agent",
            ),
        ]

    return []


def all_physics_parameter_schemas() -> list[ParameterSchema]:
    schemas: list[ParameterSchema] = []
    for desc in list_physics_descriptors():
        schemas.extend(desc.parameter_schema)
    return schemas


def _segment_length(project: SimulationProject, side: str) -> float:
    for seg in project.model.geometry.segments:
        if side in seg.name.lower():
            return seg.length
    return 2e-4
