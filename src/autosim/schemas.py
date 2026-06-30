"""Core data schemas for AutoSim."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class DragModelType(str, Enum):
    LINEAR = "linear"
    QUADRATIC = "quadratic"
    POLYNOMIAL = "polynomial"
    CUSTOM = "custom"


class AgentBackend(str, Enum):
    RULES = "rules"
    DEEPSEEK = "deepseek"
    HYBRID = "hybrid"


class AgentConfig(BaseModel):
    backend: AgentBackend = AgentBackend.HYBRID
    probe_window: int = 10
    v_max: float = 500.0
    energy_drift_max: float = 1e6


class IterationConfig(BaseModel):
    max_trials: int = 5
    stop_on: Literal["recommend_next", "max_trials"] = "recommend_next"


class SimInput(BaseModel):
    mass: float = 1.0
    gravity: float = 9.81
    y0: float = 100.0
    v0: float = 0.0
    ground_y: float = 0.0
    drag_model: DragModelType = DragModelType.QUADRATIC
    drag_params: dict[str, Any] = Field(default_factory=dict)
    t_max: float = 30.0
    probe_interval: float = 0.1
    dt: float = 0.01
    agent: AgentConfig = Field(default_factory=AgentConfig)
    iteration: IterationConfig = Field(default_factory=IterationConfig)

    def model_copy_with_params(self, params: dict[str, Any]) -> SimInput:
        """Merge suggested params into a new SimInput."""
        data = self.model_dump()
        for key, value in params.items():
            if key in ("mass", "gravity", "y0", "v0", "ground_y", "t_max", "probe_interval", "dt"):
                data[key] = value
            elif key == "drag_model":
                data["drag_model"] = value
            else:
                data.setdefault("drag_params", {})
                data["drag_params"][key] = value
        return SimInput.model_validate(data)


class SimState(BaseModel):
    t: float
    y: float
    v: float
    a: float


class ProbeSnapshot(BaseModel):
    t: float
    y: float
    v: float
    a: float
    ke: float
    pe: float
    energy_drift: float
    distance_to_ground: float
    is_diverging: bool
    is_nan: bool
    drag_force: float
    theory_probes: dict[str, Any] = Field(default_factory=dict)


class AgentAction(str, Enum):
    CONTINUE = "continue"
    EARLY_STOP = "early_stop"
    ADJUST_SEARCH_SPACE = "adjust_search_space"
    EXPLAIN_FAILURE = "explain_failure"
    RECOMMEND_NEXT = "recommend_next"


class AgentDecision(BaseModel):
    action: AgentAction
    reason: str
    confidence: float = 1.0
    suggested_params: dict[str, Any] | None = None
    search_space_patch: dict[str, Any] | None = None


class TrajectoryPoint(BaseModel):
    t: float
    y: float
    v: float
    a: float
    drag_force: float


class TrialResult(BaseModel):
    trial_index: int = 0
    input: SimInput
    trajectory: list[TrajectoryPoint] = Field(default_factory=list)
    probes: list[ProbeSnapshot] = Field(default_factory=list)
    decisions: list[AgentDecision] = Field(default_factory=list)
    impact_time: float | None = None
    impact_velocity: float | None = None
    terminal_velocity_estimate: float | None = None
    early_stopped: bool = False
    stop_reason: str = "completed"
    final_probe: ProbeSnapshot | None = None


class RunConfig(BaseModel):
    """Top-level config loaded from YAML."""

    mass: float = 1.0
    gravity: float = 9.81
    y0: float = 100.0
    v0: float = 0.0
    ground_y: float = 0.0
    drag_model: DragModelType = DragModelType.QUADRATIC
    drag_params: dict[str, Any] = Field(default_factory=dict)
    t_max: float = 30.0
    probe_interval: float = 0.1
    dt: float = 0.01
    agent: AgentConfig = Field(default_factory=AgentConfig)
    iteration: IterationConfig = Field(default_factory=IterationConfig)

    def to_sim_input(self) -> SimInput:
        return SimInput.model_validate(self.model_dump())
