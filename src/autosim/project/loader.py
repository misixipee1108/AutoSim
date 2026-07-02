"""Load SimulationProject from JSON/YAML files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from autosim.project.schemas import SimulationProject


def load_project_json(text: str) -> SimulationProject:
    data = json.loads(text)
    return SimulationProject.model_validate(data)


def load_project(path: str | Path) -> SimulationProject:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        data: dict[str, Any] = yaml.safe_load(text)
        return SimulationProject.model_validate(data)
    return load_project_json(text)


def default_pn_stationary_project() -> SimulationProject:
    """Return the MVP PN stationary Poisson project template."""
    from autosim.project.templates import pn_si_stationary_template

    return pn_si_stationary_template()
