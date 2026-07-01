"""Rule-based agent for PN junction Newton monitoring."""

from __future__ import annotations

from autosim.pn.schemas import (
    PnAgentAction,
    PnAgentConfig,
    PnAgentDecision,
    PnNewtonProbe,
    PnSimInput,
)


class PnRulesAgent:
    def __init__(self, config: PnAgentConfig) -> None:
        self.config = config

    def evaluate_mid_run(
        self,
        probe: PnNewtonProbe,
        sim_input: PnSimInput,
    ) -> PnAgentDecision:
        if probe.max_electric_field > sim_input.breakdown.E_crit * 0.95:
            return PnAgentDecision(
                action=PnAgentAction.MARK_AS_INFEASIBLE,
                reason=f"Electric field near breakdown limit ({probe.max_electric_field:.2e} V/cm)",
                confidence=0.9,
                suggested_params={"Vapp": sim_input.Vapp * 0.8},
            )
        if probe.is_nan:
            return PnAgentDecision(
                action=PnAgentAction.EARLY_STOP,
                reason="NaN detected in Newton iteration",
                confidence=1.0,
            )
        if probe.is_unphysical:
            return PnAgentDecision(
                action=PnAgentAction.EARLY_STOP,
                reason="Negative carrier concentration detected",
                confidence=1.0,
            )
        if probe.convergence_risk_score > 0.8:
            return PnAgentDecision(
                action=PnAgentAction.SWITCH_SOLVER,
                reason=f"High convergence risk ({probe.convergence_risk_score:.2f})",
                confidence=0.85,
                suggested_params={"solver": {"method": "newton_line_search"}},
            )
        if probe.exp_clamped:
            return PnAgentDecision(
                action=PnAgentAction.INCREASE_DAMPING,
                reason="Boltzmann exponent clamped; reduce damping or bias step",
                confidence=0.9,
                suggested_params={"damping": max(sim_input.damping * 0.5, 0.05)},
            )
        if probe.jacobian_condition_estimate > self.config.jacobian_cond_max:
            return PnAgentDecision(
                action=PnAgentAction.ADJUST_DAMPING,
                reason=f"Jacobian ill-conditioned (cond={probe.jacobian_condition_estimate:.2e})",
                confidence=0.85,
                suggested_params={"damping": max(sim_input.damping * 0.5, 0.05)},
            )
        if sim_input.bias_scan.enabled and probe.stalled:
            return PnAgentDecision(
                action=PnAgentAction.REDUCE_BIAS_STEP,
                reason="Newton stalled during bias sweep; reduce bias step",
                confidence=0.75,
                suggested_params={
                    "bias_scan": {
                        "Vapp_step": max(sim_input.bias_scan.Vapp_step * 0.5, 0.01),
                    }
                },
            )
        if probe.stalled:
            return PnAgentDecision(
                action=PnAgentAction.REFINE_MESH,
                reason="Newton residual stalled; refine junction mesh",
                confidence=0.8,
                suggested_params={
                    "Nx": int(sim_input.Nx * 1.5),
                    "junction_refinement": {
                        "enabled": True,
                        "ratio": sim_input.junction_refinement.ratio,
                    },
                },
            )
        if probe.residual_reduction_rate > (1.0 - self.config.residual_stall_threshold):
            return PnAgentDecision(
                action=PnAgentAction.CONTINUE,
                reason="Slow but progressing convergence",
                confidence=0.7,
            )
        return PnAgentDecision(
            action=PnAgentAction.CONTINUE,
            reason="Newton iteration progressing",
            confidence=0.9,
        )

    def evaluate_post_run(
        self,
        sim_input: PnSimInput,
        probes: list[PnNewtonProbe],
        converged: bool,
        stop_reason: str,
    ) -> PnAgentDecision:
        if not converged:
            return PnAgentDecision(
                action=PnAgentAction.EXPLAIN_FAILURE,
                reason=stop_reason,
                confidence=1.0,
                suggested_params={
                    "damping": max(sim_input.damping * 0.5, 0.1),
                    "Nx": int(sim_input.Nx * 1.25),
                },
            )
        last = probes[-1] if probes else None
        if last and last.scaled_residual_norm > sim_input.tol * 10:
            return PnAgentDecision(
                action=PnAgentAction.RECOMMEND_NEXT_PARAMETERS,
                reason="Approximate convergence; refine mesh for tighter scaled residual",
                confidence=0.8,
                suggested_params={"Nx": int(sim_input.Nx * 1.5), "tol": sim_input.tol * 0.1},
            )
        return PnAgentDecision(
            action=PnAgentAction.RECOMMEND_NEXT_PARAMETERS,
            reason="Simulation converged successfully",
            confidence=0.9,
            suggested_params={"Vapp": sim_input.Vapp + 0.05},
        )

    def veto(self, decision: PnAgentDecision, probe: PnNewtonProbe) -> PnAgentDecision:
        if probe.is_nan or probe.is_unphysical:
            return PnAgentDecision(
                action=PnAgentAction.EARLY_STOP,
                reason=f"Rules veto: {decision.reason}",
                confidence=1.0,
            )
        return decision
