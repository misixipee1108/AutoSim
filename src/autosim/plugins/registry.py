"""Plugin discovery and registration."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from autosim.plugins.physics.base import PhysicsInterfacePlugin
from autosim.plugins.studies.base import StudyRunner
from autosim.project.schemas import PhysicsInterfaceDescriptor

_MANIFEST_DIR = Path(__file__).parent / "physics" / "manifests"


@lru_cache(maxsize=1)
def _physics_plugins() -> dict[str, PhysicsInterfacePlugin]:
    from autosim.plugins.physics.mechanics_0d_falling_body.plugin import Mechanics0DFallingBodyPlugin
    from autosim.plugins.physics.semiconductor_1d_dd.plugin import Semiconductor1DDdPlugin
    from autosim.plugins.physics.semiconductor_1d_poisson.plugin import Semiconductor1DPoissonPlugin

    plugins: list[PhysicsInterfacePlugin] = [
        Semiconductor1DPoissonPlugin(),
        Semiconductor1DDdPlugin(),
        Mechanics0DFallingBodyPlugin(),
    ]
    return {p.interface_id: p for p in plugins}


@lru_cache(maxsize=1)
def _study_runners() -> dict[str, StudyRunner]:
    from autosim.plugins.studies.bias_sweep import BiasSweepStudyRunner
    from autosim.plugins.studies.cv_sweep import CvSweepStudyRunner
    from autosim.plugins.studies.optimization import OptimizationStudyRunner
    from autosim.plugins.studies.parameter_sweep import ParameterSweepStudyRunner
    from autosim.plugins.studies.stationary import StationaryStudyRunner
    from autosim.plugins.studies.time_dependent import TimeDependentStudyRunner

    runners: list[StudyRunner] = [
        StationaryStudyRunner(),
        BiasSweepStudyRunner(),
        CvSweepStudyRunner(),
        TimeDependentStudyRunner(),
        OptimizationStudyRunner(),
        ParameterSweepStudyRunner(),
    ]
    return {r.study_type: r for r in runners}


def get_physics_plugin(interface_id: str) -> PhysicsInterfacePlugin:
    plugins = _physics_plugins()
    if interface_id not in plugins:
        raise KeyError(f"Unknown physics interface: {interface_id}")
    return plugins[interface_id]


def list_physics_plugins() -> list[PhysicsInterfacePlugin]:
    return list(_physics_plugins().values())


def list_physics_descriptors() -> list[PhysicsInterfaceDescriptor]:
    return [p.get_descriptor() for p in list_physics_plugins()]


def get_physics_descriptor(interface_id: str) -> PhysicsInterfaceDescriptor:
    return get_physics_plugin(interface_id).get_descriptor()


def get_study_runner(study_type: str) -> StudyRunner:
    runners = _study_runners()
    if study_type not in runners:
        raise KeyError(f"Study type not implemented: {study_type}")
    return runners[study_type]


def list_study_types() -> list[str]:
    return list(_study_runners().keys())


def load_physics_manifest(interface_id: str) -> dict:
    path = _MANIFEST_DIR / f"{interface_id}.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)
