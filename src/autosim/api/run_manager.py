"""Background run execution and state management."""

from __future__ import annotations

import asyncio
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from autosim.api.adapters.base import RunCallbacks
from autosim.api.schemas import (
    ConvergenceSeries,
    CreateRunRequest,
    RunStatus,
    StreamEvent,
    UnifiedAgentDecision,
    UnifiedProbe,
    UnifiedRunResult,
)

_PROBE_TO_CONVERGENCE: dict[str, tuple[str, str]] = {
    "residual_norm": ("residual", "Newton Residual"),
    "scaled_residual_norm": ("scaled_residual", "Scaled Residual"),
    "scaled_delta_norm": ("scaled_delta", "Scaled Newton Step"),
    "energy_drift": ("energy_drift", "Energy Drift"),
}


@dataclass
class RunState:
    run_id: str
    model_id: str
    status: RunStatus = RunStatus.PENDING
    result: UnifiedRunResult | None = None
    logs: list[str] = field(default_factory=list)
    event_queues: list[asyncio.Queue] = field(default_factory=list)
    error: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def append_log(self, message: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        line = f"[{ts}] {message}"
        with self._lock:
            self.logs.append(line)
        self._broadcast(StreamEvent(event="log", data={"message": line}))

    def _broadcast(self, event: StreamEvent) -> None:
        for queue in self.event_queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass


class RunManager:
    def __init__(self) -> None:
        self._runs: dict[str, RunState] = {}
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._lock = threading.Lock()

    def create_run(self, request: CreateRunRequest) -> RunState:
        if not request.project:
            raise ValueError("SimulationProject payload required (v2 API)")
        run_id = str(uuid.uuid4())[:8]
        project_id = request.project.get("project_id", "simulation_project_v2")
        state = RunState(run_id=run_id, model_id=str(project_id))
        with self._lock:
            self._runs[run_id] = state
        self._executor.submit(self._execute_project_run, state, request)
        return state

    def get_run(self, run_id: str) -> RunState | None:
        return self._runs.get(run_id)

    def subscribe(self, run_id: str) -> asyncio.Queue | None:
        state = self.get_run(run_id)
        if state is None:
            return None
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        state.event_queues.append(queue)
        return queue

    def _execute_project_run(self, state: RunState, request: CreateRunRequest) -> None:
        from autosim.api.adapters.project import ProjectAdapter

        state.status = RunStatus.RUNNING
        state.append_log(f"Run started for {state.model_id}")
        self._broadcast_status(state, RunStatus.RUNNING)

        try:
            adapter = ProjectAdapter()
            project = adapter.validate_project(request.project or {})
            if request.active_study_id:
                project = project.model_copy(update={"active_study_id": request.active_study_id})
            study = adapter.get_active_study(project)
            if request.agent and project.studies:
                agent = study.agent.model_copy(update={"backend": request.agent}) if study.agent else None
                if agent:
                    studies = []
                    for s in project.studies:
                        if s.study_id == study.study_id:
                            studies.append(s.model_copy(update={"agent": agent}))
                        else:
                            studies.append(s)
                    project = project.model_copy(update={"studies": studies})
                    study = adapter.get_active_study(project)

            callbacks = RunCallbacks(
                on_probe=lambda p: self._on_probe(state, p),
                on_decision=lambda d: self._on_decision(state, d),
                on_log=lambda msg: state.append_log(msg),
            )

            result = adapter.run_study(
                project,
                study=study,
                callbacks=callbacks,
                max_trials=request.max_trials,
            )

            if isinstance(result, list):
                unified = adapter.normalize_trials(state.run_id, project, result, logs=state.logs)
            else:
                unified = adapter.normalize_result(state.run_id, project, result, logs=state.logs)

            state.result = unified
            state.status = unified.status
            state.append_log("Run completed")
            self._broadcast_status(state, unified.status)
            self._broadcast(state, StreamEvent(event="complete", data=unified.model_dump(mode="json")))

        except Exception as exc:
            state.status = RunStatus.FAILED
            state.error = str(exc)
            state.append_log(f"Run failed: {exc}")
            state.result = UnifiedRunResult(
                run_id=state.run_id,
                model_id=state.model_id,
                status=RunStatus.FAILED,
                logs=state.logs,
                error=str(exc),
            )
            self._broadcast_status(state, RunStatus.FAILED)
            self._broadcast(state, StreamEvent(event="error", data={"error": str(exc)}))

    def _on_probe(self, state: RunState, probe: UnifiedProbe) -> None:
        if state.result is None:
            state.result = UnifiedRunResult(
                run_id=state.run_id,
                model_id=state.model_id,
                status=RunStatus.RUNNING,
                logs=state.logs,
            )
        by_name = {p.name: p for p in state.result.probes}
        by_name[probe.name] = probe
        state.result.probes = list(by_name.values())
        conv_spec = _PROBE_TO_CONVERGENCE.get(probe.name)
        if conv_spec and probe.x and probe.y:
            series_name, series_label = conv_spec
            conv_list = state.result.convergence
            target = next((c for c in conv_list if c.name == series_name), None)
            if target is None:
                target = ConvergenceSeries(
                    name=series_name,
                    label=series_label,
                    unit="",
                    x=[],
                    y=[],
                    x_label="Iteration",
                )
                conv_list.append(target)
            target.x = target.x + list(probe.x)
            target.y = target.y + list(probe.y)
        self._broadcast(state, StreamEvent(event="probe", data=probe.model_dump(mode="json")))

    def _on_decision(self, state: RunState, decision: UnifiedAgentDecision) -> None:
        if state.result is None:
            state.result = UnifiedRunResult(
                run_id=state.run_id,
                model_id=state.model_id,
                status=RunStatus.RUNNING,
                logs=state.logs,
            )
        state.result.decisions.append(decision)
        state.append_log(f"Agent decision: {decision.action.value} — {decision.reason}")
        self._broadcast(state, StreamEvent(event="decision", data=decision.model_dump(mode="json")))

    def _broadcast_status(self, state: RunState, status: RunStatus) -> None:
        self._broadcast(state, StreamEvent(event="status", data={"status": status.value}))

    @staticmethod
    def _broadcast(state: RunState, event: StreamEvent) -> None:
        state._broadcast(event)


run_manager = RunManager()
