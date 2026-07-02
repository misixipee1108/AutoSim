"""Fixed three-root model tree schema builder."""

from __future__ import annotations

from typing import Any

from autosim.plugins.registry import list_physics_descriptors
from autosim.project.physics_tree import group_slug, group_tree_label, physics_field_label
from autosim.project.schemas import SimulationProject, StudyDefinition


def build_model_tree_schema(project: SimulationProject | None = None) -> dict[str, Any]:
    """Return the COMSOL-style three-section model tree for the frontend."""
    studies = project.studies if project else []
    physics_children: list[dict[str, Any]] = []

    if project:
        for iface in project.model.physics_interfaces:
            desc = next(
                (d for d in list_physics_descriptors() if d.interface_id == iface.interface_id),
                None,
            )
            groups = desc.tree_parameter_groups if desc and desc.tree_parameter_groups else ["Settings"]
            field_label = physics_field_label(desc.category if desc else "general")
            group_children = [
                {
                    "id": f"model.physics_interfaces.{iface.instance_id}.{group_slug(group)}",
                    "label": group_tree_label(group),
                    "kind": "node",
                    "parameter_refs": [
                        f"model.physics_interfaces.{iface.instance_id}.settings",
                    ],
                    "interface_id": iface.interface_id,
                    "instance_id": iface.instance_id,
                    "parameter_group": group,
                }
                for group in groups
            ]
            physics_children.append(
                {
                    "id": f"model.physics_interfaces.{iface.instance_id}",
                    "label": field_label,
                    "kind": "collection",
                    "interface_id": iface.interface_id,
                    "instance_id": iface.instance_id,
                    "physics_category": desc.category if desc else "general",
                    "children": group_children,
                }
            )
    else:
        for desc in list_physics_descriptors():
            physics_children.append(
                {
                    "id": f"model.physics_interfaces.template.{desc.interface_id}",
                    "label": desc.name,
                    "kind": "template",
                    "interface_id": desc.interface_id,
                }
            )

    study_children: list[dict[str, Any]] = []
    for study in studies:
        study_children.extend(_study_tree_nodes(study))

    return {
        "schema_version": "2.0",
        "roots": [
            {
                "id": "model",
                "label": "Model",
                "kind": "section",
                "children": [
                    {
                        "id": "model.geometry",
                        "label": "Geometry",
                        "kind": "node",
                        "parameter_refs": ["model.geometry"],
                    },
                    {
                        "id": "model.domain",
                        "label": "Domain",
                        "kind": "node",
                        "parameter_refs": ["model.domains"],
                    },
                    {
                        "id": "model.material",
                        "label": "Material",
                        "kind": "node",
                        "parameter_refs": ["model.materials"],
                    },
                    {
                        "id": "model.physics_interfaces",
                        "label": "Physics Interfaces",
                        "kind": "collection",
                        "children": physics_children,
                    },
                    {
                        "id": "model.variables",
                        "label": "Variables",
                        "kind": "node",
                        "parameter_refs": ["model.variables"],
                    },
                    {
                        "id": "model.boundary_conditions",
                        "label": "Boundary Conditions",
                        "kind": "node",
                        "parameter_refs": ["model.boundary_conditions"],
                    },
                    {
                        "id": "model.initial_conditions",
                        "label": "Initial Conditions",
                        "kind": "node",
                        "parameter_refs": ["model.initial_conditions"],
                    },
                    {
                        "id": "model.source_terms",
                        "label": "Source Terms",
                        "kind": "node",
                        "parameter_refs": ["model.source_terms"],
                    },
                    {
                        "id": "model.mesh",
                        "label": "Mesh",
                        "kind": "node",
                        "parameter_refs": ["model.mesh"],
                    },
                ],
            },
            {
                "id": "studies",
                "label": "Simulation",
                "kind": "section",
                "children": study_children,
            },
            {
                "id": "results",
                "label": "Results",
                "kind": "section",
                "children": [
                    {
                        "id": "results.output_variables",
                        "label": "Output Variables",
                        "kind": "node",
                        "parameter_refs": ["results.output_variables"],
                    },
                    {
                        "id": "results.visualizations",
                        "label": "Visualizations",
                        "kind": "node",
                        "parameter_refs": ["results.visualizations"],
                    },
                    {
                        "id": "results.postprocessing",
                        "label": "Postprocessing",
                        "kind": "node",
                        "parameter_refs": ["results.postprocessing"],
                    },
                    {
                        "id": "results.reports",
                        "label": "Reports",
                        "kind": "node",
                        "parameter_refs": ["results.reports"],
                    },
                ],
            },
        ],
    }


def _study_tree_nodes(study: StudyDefinition) -> list[dict[str, Any]]:
    label = study.label or study.study_id
    base = f"studies.{study.study_id}"
    return [
        {
            "id": base,
            "label": label,
            "kind": "study",
            "study_id": study.study_id,
            "study_type": study.study_type,
            "children": [
                {
                    "id": f"{base}.study_params",
                    "label": "Study Settings",
                    "kind": "node",
                    "parameter_refs": [f"{base}.parameters"],
                },
                {
                    "id": f"{base}.solver_sequence",
                    "label": "Solver Sequence",
                    "kind": "node",
                    "parameter_refs": [f"{base}.solver_sequence"],
                },
                {
                    "id": f"{base}.agent",
                    "label": "Agent",
                    "kind": "node",
                    "parameter_refs": [f"{base}.agent"],
                },
            ],
        }
    ]
