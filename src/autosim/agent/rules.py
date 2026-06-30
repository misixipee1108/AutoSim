"""Rule-based agent for simulation monitoring."""

from __future__ import annotations

from autosim.schemas import AgentAction, AgentConfig, AgentDecision, ProbeSnapshot, SimInput


class RulesAgent:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    def evaluate_mid_run(
        self,
        probe: ProbeSnapshot,
        sim_input: SimInput,
    ) -> AgentDecision:
        if probe.is_nan:
            return AgentDecision(
                action=AgentAction.EARLY_STOP,
                reason="NaN detected in state variables",
                confidence=1.0,
            )
        if probe.is_diverging:
            return AgentDecision(
                action=AgentAction.EARLY_STOP,
                reason=f"Velocity {probe.v:.2f} exceeds limit or energy drift too large",
                confidence=1.0,
            )
        if probe.distance_to_ground <= 0:
            return AgentDecision(
                action=AgentAction.CONTINUE,
                reason="Impact reached",
                confidence=1.0,
            )
        return AgentDecision(
            action=AgentAction.CONTINUE,
            reason="Simulation progressing normally",
            confidence=1.0,
        )

    def evaluate_post_run(
        self,
        sim_input: SimInput,
        probes: list[ProbeSnapshot],
        early_stopped: bool,
        stop_reason: str,
    ) -> AgentDecision:
        if early_stopped:
            return AgentDecision(
                action=AgentAction.EXPLAIN_FAILURE,
                reason=stop_reason,
                confidence=1.0,
                suggested_params=self._suggest_recovery(sim_input),
            )

        last = probes[-1] if probes else None
        if last and last.distance_to_ground > 0.01:
            return AgentDecision(
                action=AgentAction.RECOMMEND_NEXT,
                reason="Simulation ended before ground impact; increase t_max",
                confidence=0.8,
                suggested_params={"t_max": sim_input.t_max * 1.5},
            )

        return AgentDecision(
            action=AgentAction.RECOMMEND_NEXT,
            reason="Trial completed successfully",
            confidence=0.9,
            suggested_params=self._suggest_variation(sim_input),
        )

    def _suggest_recovery(self, sim_input: SimInput) -> dict:
        params = dict(sim_input.drag_params)
        if "c1" in params:
            params["c1"] = params["c1"] * 0.5
        if "c2" in params:
            params["c2"] = params["c2"] * 0.5
        if "coeffs" in params:
            params["coeffs"] = [c * 0.5 for c in params["coeffs"]]
        return params

    def _suggest_variation(self, sim_input: SimInput) -> dict:
        params = dict(sim_input.drag_params)
        if "c2" in params:
            params["c2"] = params["c2"] * 1.1
        elif "c1" in params:
            params["c1"] = params["c1"] * 1.1
        return params

    def veto(self, decision: AgentDecision, probe: ProbeSnapshot) -> AgentDecision:
        """Rules override: safety veto for hybrid mode."""
        if probe.is_nan or probe.is_diverging:
            return AgentDecision(
                action=AgentAction.EARLY_STOP,
                reason=f"Rules veto: {decision.reason}",
                confidence=1.0,
            )
        return decision
