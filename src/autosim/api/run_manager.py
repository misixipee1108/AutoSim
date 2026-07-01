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
from autosim.api.model_registry.registry import get_adapter
from autosim.api.schemas import (
    ConvergenceSeries,
    CreateRunRequest,
    RunStatus,
    StreamEvent,
    TrialSummary,
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
        run_id = str(uuid.uuid4())[:8]
        state = RunState(run_id=run_id, model_id=request.model_id)
        with self._lock:
            self._runs[run_id] = state
        self._executor.submit(self._execute_run, state, request)
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

    def _execute_run(self, state: RunState, request: CreateRunRequest) -> None:
        state.status = RunStatus.RUNNING
        state.append_log(f"Run started for model {request.model_id}")
        self._broadcast_status(state, RunStatus.RUNNING)

        try:
            adapter = get_adapter(request.model_id)
            config = adapter.validate_config(request.config)
            if request.agent:
                from autosim.api.adapters.base import apply_agent_override

                data = config.model_dump()
                flat = apply_agent_override(data, request.agent)
                config = adapter.validate_config(flat)

            if request.max_trials > 1:
                data = config.model_dump()
                data.setdefault("iteration", {})
                data["iteration"]["max_trials"] = request.max_trials
                config = adapter.validate_config(data)

            callbacks = RunCallbacks(
                on_probe=lambda p: self._on_probe(state, p),
                on_decision=lambda d: self._on_decision(state, d),
                on_log=lambda msg: state.append_log(msg),
            )

            multi_run = request.max_trials > 1
            if hasattr(config, "bias_scan") and getattr(config.bias_scan, "enabled", False):
                multi_run = True
            if hasattr(config, "optimization") and getattr(config.optimization, "enabled", False):
                multi_run = True

            if multi_run:
                results = adapter.run_iteration(config, callbacks=callbacks)
                last = results[-1]
                unified = adapter.normalize_result(
                    state.run_id, last, logs=state.logs, all_trials=results
                )
                unified.trials = [
                    TrialSummary(
                        trial_index=r.trial_index,
                        status=RunStatus.COMPLETED if not r.early_stopped else RunStatus.EARLY_STOPPED,
                        stop_reason=r.stop_reason,
                        early_stopped=r.early_stopped,
                        scalars=adapter.normalize_result(state.run_id, r).scalars,
                    )
                    for r in results
                ]
            else:
                result = adapter.run_trial(config, trial_index=0, callbacks=callbacks)
                unified = adapter.normalize_result(state.run_id, result, logs=state.logs)

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
