"""Falling block simulation adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from autosim.api.adapters.base import RunCallbacks, apply_agent_override, flatten_config
from autosim.api.schemas import (
    ConvergenceSeries,
    RunStatus,
    ScalarMetric,
    TimeSeries,
    UnifiedAction,
    UnifiedAgentDecision,
    UnifiedProbe,
    UnifiedRunResult,
)
from autosim.orchestrator.runner import run_iteration, run_trial
from autosim.schemas import AgentAction, AgentDecision, ProbeSnapshot, RunConfig, TrialResult


_FB_ACTION_MAP: dict[str, UnifiedAction] = {
    AgentAction.CONTINUE.value: UnifiedAction.CONTINUE,
    AgentAction.EARLY_STOP.value: UnifiedAction.EARLY_STOP,
    AgentAction.ADJUST_SEARCH_SPACE.value: UnifiedAction.ADJUST_PARAMS,
    AgentAction.EXPLAIN_FAILURE.value: UnifiedAction.EXPLAIN_FAILURE,
    AgentAction.RECOMMEND_NEXT.value: UnifiedAction.RECOMMEND_NEXT,
}


class FallingBlockAdapter:
    model_id = "falling_block"

    def validate_config(self, raw: dict[str, Any]) -> RunConfig:
        flat = flatten_config(raw)
        return RunConfig.model_validate(flat)

    def run_trial(
        self,
        config: RunConfig,
        trial_index: int = 0,
        callbacks: RunCallbacks | None = None,
    ) -> TrialResult:
        sim_input = config.to_sim_input()
        if callbacks is None:
            return run_trial(sim_input, trial_index=trial_index)

        from autosim.agent.deepseek import AgentService
        from autosim.simulator.falling_block import simulate_falling_block

        agent = AgentService(sim_input.agent)
        probe_history: list[ProbeSnapshot] = []

        def on_probe(probe: ProbeSnapshot):
            probe_history.append(probe)
            unified = self.normalize_probe(probe)
            if callbacks.on_probe:
                callbacks.on_probe(unified)
            decision = agent.evaluate_mid_run(probe, sim_input, probe_history)
            if decision.action == AgentAction.EARLY_STOP:
                unified_dec = self.normalize_decision(decision)
                if callbacks.on_decision:
                    callbacks.on_decision(unified_dec)
                return decision
            return None

        result = simulate_falling_block(sim_input, on_probe=on_probe, trial_index=trial_index)
        post_decision = agent.evaluate_post_run(
            sim_input, result.probes, result.early_stopped, result.stop_reason
        )
        result.decisions.append(post_decision)
        unified_dec = self.normalize_decision(post_decision)
        if callbacks.on_decision:
            callbacks.on_decision(unified_dec)
        return result

    def run_iteration(
        self,
        config: RunConfig,
        callbacks: RunCallbacks | None = None,
    ) -> list[TrialResult]:
        if callbacks is None:
            return run_iteration(config.to_sim_input())

        results: list[TrialResult] = []
        current = config.to_sim_input()
        for trial_idx in range(current.iteration.max_trials):
            if callbacks.on_log:
                callbacks.on_log(f"Starting trial {trial_idx}")
            trial_config = RunConfig.model_validate(current.model_dump())
            result = self.run_trial(trial_config, trial_index=trial_idx, callbacks=callbacks)
            results.append(result)
            post = [d for d in result.decisions if d.action == AgentAction.RECOMMEND_NEXT]
            if not post or not post[-1].suggested_params:
                break
            current = current.model_copy_with_params(post[-1].suggested_params)
        return results

    def normalize_probe(self, raw: ProbeSnapshot) -> UnifiedProbe:
        return UnifiedProbe(
            name="probe_snapshot",
            label="Probe Snapshot",
            type="scalar",
            value=raw.energy_drift,
            timestamp=datetime.now(timezone.utc).isoformat(),
            x=[raw.t],
            y=[raw.energy_drift],
        )

    def normalize_decision(self, raw: AgentDecision) -> UnifiedAgentDecision:
        action = _FB_ACTION_MAP.get(raw.action.value, UnifiedAction.CONTINUE)
        return UnifiedAgentDecision(
            action=action,
            reason=raw.reason,
            confidence=raw.confidence,
            suggested_params=raw.suggested_params,
            raw_action=raw.action.value,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def normalize_result(
        self,
        run_id: str,
        raw: TrialResult,
        status: str = "completed",
        logs: list[str] | None = None,
    ) -> UnifiedRunResult:
        run_status = RunStatus.EARLY_STOPPED if raw.early_stopped else RunStatus(status)
        ts = [p.t for p in raw.trajectory]
        profiles_time: list[TimeSeries] = [
            TimeSeries(name="position", label="Position", unit="m", t=ts, y=[p.y for p in raw.trajectory]),
            TimeSeries(name="velocity", label="Velocity", unit="m/s", t=ts, y=[p.v for p in raw.trajectory]),
            TimeSeries(name="acceleration", label="Acceleration", unit="m/s²", t=ts, y=[p.a for p in raw.trajectory]),
        ]
        conv = ConvergenceSeries(
            name="energy_drift",
            label="Energy Drift",
            unit="J",
            x=[p.t for p in raw.probes],
            y=[p.energy_drift for p in raw.probes],
            x_label="Time (s)",
            y_label="Energy Drift (J)",
        )
        latest = raw.probes[-1] if raw.probes else raw.final_probe
        probes: list[UnifiedProbe] = []
        if latest:
            probes = [
                UnifiedProbe(name="energy_drift", label="Energy Drift", type="scalar", unit="J", value=latest.energy_drift),
                UnifiedProbe(name="drag_force", label="Drag Force", type="scalar", unit="N", value=latest.drag_force),
                UnifiedProbe(name="is_diverging", label="Diverging", type="boolean", value=latest.is_diverging),
                UnifiedProbe(name="is_nan", label="NaN Detected", type="boolean", value=latest.is_nan),
                UnifiedProbe(name="distance_to_ground", label="Distance to Ground", type="scalar", unit="m", value=latest.distance_to_ground),
            ]
        scalars: dict[str, ScalarMetric] = {}
        if raw.impact_time is not None:
            scalars["impact_time"] = ScalarMetric(value=raw.impact_time, unit="s", label="Impact Time")
        if raw.impact_velocity is not None:
            scalars["impact_velocity"] = ScalarMetric(value=raw.impact_velocity, unit="m/s", label="Impact Velocity")
        if raw.terminal_velocity_estimate is not None:
            scalars["terminal_velocity"] = ScalarMetric(
                value=raw.terminal_velocity_estimate, unit="m/s", label="Terminal Velocity"
            )
        return UnifiedRunResult(
            run_id=run_id,
            model_id=self.model_id,
            status=run_status,
            trial_index=raw.trial_index,
            scalars=scalars,
            time_series=profiles_time,
            convergence=[conv],
            probes=probes,
            decisions=[self.normalize_decision(d) for d in raw.decisions],
            logs=logs or [],
        )

    @staticmethod
    def build_config(raw: dict[str, Any], agent: str | None = None) -> RunConfig:
        flat = apply_agent_override(flatten_config(raw), agent)
        return RunConfig.model_validate(flat)
