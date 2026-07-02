"""Read/write nested values in SimulationProject by dotted path."""

from __future__ import annotations

from typing import Any

from autosim.project.schemas import SimulationProject


def get_project_value(project: SimulationProject, path: str) -> Any:
    data = project.model_dump()
    parts = path.split(".")
    cursor: Any = data
    for part in parts:
        if isinstance(cursor, list):
            idx = int(part)
            cursor = cursor[idx]
        elif isinstance(cursor, dict):
            cursor = cursor[part]
        else:
            return None
    return cursor


def set_project_value(project: SimulationProject, path: str, value: Any) -> SimulationProject:
    data = project.model_dump()
    parts = path.split(".")
    cursor: Any = data
    for part in parts[:-1]:
        if isinstance(cursor, list):
            cursor = cursor[int(part)]
        else:
            if part not in cursor:
                cursor[part] = {}
            cursor = cursor[part]
    last = parts[-1]
    if isinstance(cursor, list):
        cursor[int(last)] = value
    else:
        cursor[last] = value
    return SimulationProject.model_validate(data)
