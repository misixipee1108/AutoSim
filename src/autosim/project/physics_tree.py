"""Shared labels and path helpers for physics-interface model tree nodes."""

from __future__ import annotations

PHYSICS_FIELD_LABELS: dict[str, str] = {
    "semiconductor": "Semiconductor",
    "mechanics": "Mechanics",
    "thermal": "Thermal",
    "optics": "Optics",
}

GROUP_TREE_LABELS: dict[str, str] = {
    "Physics": "Physics Model",
    "Doping": "Doping",
    "Recombination": "Recombination",
    "Body": "Body",
    "Drag": "Drag",
    "Integration": "Integration",
}

GROUP_SLUGS: dict[str, str] = {
    "Physics": "physics",
    "Doping": "doping",
    "Recombination": "recombination",
    "Body": "body",
    "Drag": "drag",
    "Integration": "integration",
}

SLUG_TO_GROUP: dict[str, str] = {v: k for k, v in GROUP_SLUGS.items()}


def physics_field_label(category: str) -> str:
    return PHYSICS_FIELD_LABELS.get(category, category.replace("_", " ").title())


def group_tree_label(group: str) -> str:
    return GROUP_TREE_LABELS.get(group, group)


def group_slug(group: str) -> str:
    return GROUP_SLUGS.get(group, group.lower().replace(" ", "_"))


def parse_physics_interface_tree_path(tree_path: str) -> tuple[str | None, str | None]:
    """Return (instance_id, group_name) for physics-interface parameter paths."""
    if not tree_path.startswith("model.physics_interfaces."):
        return None, None
    parts = tree_path.split(".")
    if len(parts) < 3:
        return None, None
    instance_id = parts[2]
    if instance_id.startswith("template"):
        return None, None
    if len(parts) < 4:
        return instance_id, None
    group_name = SLUG_TO_GROUP.get(parts[3])
    return instance_id, group_name
