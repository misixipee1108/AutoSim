"""Study runner plugin protocol."""

from __future__ import annotations

from typing import Any, Protocol

from autosim.api.adapters.base import RunCallbacks
from autosim.project.schemas import SimulationProject, StudyDefinition


class StudyRunner(Protocol):
    study_type: str

    def run(
        self,
        project: SimulationProject,
        study: StudyDefinition,
        callbacks: RunCallbacks | None = None,
    ) -> Any: ...
