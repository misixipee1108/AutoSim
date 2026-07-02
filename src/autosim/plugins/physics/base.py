"""Physics interface plugin protocol."""

from __future__ import annotations

from typing import Any, Protocol

from autosim.api.adapters.base import RunCallbacks
from autosim.project.schemas import (
    ModelSection,
    PhysicsInterfaceDescriptor,
    PhysicsInterfaceInstance,
    ResultsSection,
    SimulationProject,
    StudyDefinition,
)


class PhysicsInterfacePlugin(Protocol):
    interface_id: str

    def get_descriptor(self) -> PhysicsInterfaceDescriptor: ...

    def validate_instance(
        self,
        instance: PhysicsInterfaceInstance,
        model: ModelSection,
    ) -> None: ...

    def build_sim_input(
        self,
        project: SimulationProject,
        study: StudyDefinition,
        instance: PhysicsInterfaceInstance,
    ) -> Any: ...

    def run(
        self,
        sim_input: Any,
        callbacks: RunCallbacks | None = None,
        trial_index: int = 0,
    ) -> Any: ...

    def filter_outputs(
        self,
        raw_result: Any,
        results: ResultsSection,
    ) -> dict[str, Any]: ...
