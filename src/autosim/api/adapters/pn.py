"""PN junction simulation adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from autosim.api.adapters.base import RunCallbacks, apply_agent_override, flatten_config
from autosim.api.schemas import (
    ConvergenceSeries,
    ConvergenceSummaryView,
    ProfileSeries,
    RunStatus,
    ScalarMetric,
    SweepSeries,
    TimeSeries,
    TrialSummary,
    UnifiedAction,
    UnifiedAgentDecision,
    UnifiedProbe,
    UnifiedRunResult,
    ValidationMetricView,
)
from autosim.orchestrator.pn_optimizer import run_pn_optimization
from autosim.orchestrator.pn_runner import run_pn_iteration, run_pn_trial, run_pn_with_sweep
from autosim.pn.schemas import (
    PnAgentAction,
    PnAgentDecision,
    PnNewtonProbe,
    PnRunConfig,
    PnSweepResult,
    PnTrialResult,
    ValidationStatus,
)
from autosim.pn.status import (
    derive_run_status,
    run_status_to_api,
    validation_status_for_api,
)


_PN_ACTION_MAP: dict[str, UnifiedAction] = {
    PnAgentAction.CONTINUE.value: UnifiedAction.CONTINUE,
    PnAgentAction.EARLY_STOP.value: UnifiedAction.EARLY_STOP,
    PnAgentAction.ADJUST_DAMPING.value: UnifiedAction.ADJUST_PARAMS,
    PnAgentAction.INCREASE_DAMPING.value: UnifiedAction.ADJUST_PARAMS,
    PnAgentAction.REFINE_MESH.value: UnifiedAction.REFINE_MESH,
    PnAgentAction.ADJUST_BIAS_STEP.value: UnifiedAction.ADJUST_PARAMS,
    PnAgentAction.REDUCE_BIAS_STEP.value: UnifiedAction.ADJUST_PARAMS,
    PnAgentAction.CHANGE_INITIAL_GUESS.value: UnifiedAction.ADJUST_PARAMS,
    PnAgentAction.SWITCH_SOLVER.value: UnifiedAction.ADJUST_PARAMS,
    PnAgentAction.MARK_AS_INFEASIBLE.value: UnifiedAction.MARK_INFEASIBLE,
    PnAgentAction.EXPLAIN_FAILURE.value: UnifiedAction.EXPLAIN_FAILURE,
    PnAgentAction.RECOMMEND_NEXT_PARAMETERS.value: UnifiedAction.RECOMMEND_NEXT,
}


class PnAdapter:
    model_id = "pn_junction_1d"

    def validate_config(self, raw: dict[str, Any]) -> PnRunConfig:
        flat = flatten_config(raw)
        return PnRunConfig.model_validate(flat)

    def run_trial(
        self,
        config: PnRunConfig,
        trial_index: int = 0,
        callbacks: RunCallbacks | None = None,
    ) -> PnTrialResult:
        sim_input = config.to_sim_input()
        if callbacks is None:
            return run_pn_trial(sim_input, trial_index=trial_index)

        from autosim.orchestrator.pn_runner import _make_on_probe
        from autosim.agent.pn_deepseek import PnAgentService
        from autosim.pn.solve import solve_pn

        agent = PnAgentService(sim_input.agent)
        probe_history: list[PnNewtonProbe] = []
        trial_decisions: list[PnAgentDecision] = []

        def on_probe(probe: PnNewtonProbe):
            probe_history.append(probe)
            for unified in self.normalize_probes(probe):
                if callbacks.on_probe:
                    callbacks.on_probe(unified)
            decision = agent.evaluate_mid_run(probe, sim_input, probe_history)
            if decision.action in (
                PnAgentAction.EARLY_STOP,
                PnAgentAction.ADJUST_DAMPING,
                PnAgentAction.INCREASE_DAMPING,
                PnAgentAction.CHANGE_INITIAL_GUESS,
                PnAgentAction.REFINE_MESH,
                PnAgentAction.SWITCH_SOLVER,
                PnAgentAction.REDUCE_BIAS_STEP,
            ):
                unified_dec = self.normalize_decision(decision)
                if callbacks.on_decision:
                    callbacks.on_decision(unified_dec)
                return decision
            if decision.action == PnAgentAction.CONTINUE:
                trial_decisions.append(decision)
            return None

        result = solve_pn(sim_input, on_probe=on_probe, trial_index=trial_index)
        result.decisions = trial_decisions + result.decisions
        post_decision = agent.evaluate_post_run(
            sim_input, result.probes, result.converged, result.stop_reason
        )
        result.decisions.append(post_decision)
        unified_dec = self.normalize_decision(post_decision)
        if callbacks.on_decision:
            callbacks.on_decision(unified_dec)
        return result

    def run_iteration(
        self,
        config: PnRunConfig,
        callbacks: RunCallbacks | None = None,
    ) -> list[PnTrialResult]:
        sim_input = config.to_sim_input()
        if sim_input.optimization.enabled:
            results, _ = run_pn_optimization(sim_input)
            return results
        if sim_input.bias_scan.enabled:
            results, _ = run_pn_with_sweep(sim_input)
            return results
        if callbacks is None:
            return run_pn_iteration(sim_input)

        results: list[PnTrialResult] = []
        current = sim_input
        for trial_idx in range(current.iteration.max_trials):
            if callbacks.on_log:
                callbacks.on_log(f"Starting trial {trial_idx}")
            trial_config = PnRunConfig.model_validate(current.model_dump())
            result = self.run_trial(trial_config, trial_index=trial_idx, callbacks=callbacks)
            results.append(result)
            post = [d for d in result.decisions if d.action == PnAgentAction.RECOMMEND_NEXT_PARAMETERS]
            if not post or not post[-1].suggested_params:
                break
            current = current.model_copy_with_params(post[-1].suggested_params)
        return results

    def normalize_probe(self, raw: PnNewtonProbe) -> UnifiedProbe:
        probes = self.normalize_probes(raw)
        return probes[0] if probes else UnifiedProbe(
            name="residual_norm", label="Residual Norm", type="scalar", value=raw.residual_norm
        )

    def normalize_probes(self, raw: PnNewtonProbe) -> list[UnifiedProbe]:
        ts = datetime.now(timezone.utc).isoformat()
        scalar_fields = [
            ("residual_norm", "Residual Norm", raw.residual_norm, ""),
            ("scaled_residual_norm", "Scaled Residual Norm", raw.scaled_residual_norm, ""),
            ("residual_reduction_rate", "Residual Reduction Rate", raw.residual_reduction_rate, ""),
            ("delta_norm", "Newton Step Norm", raw.delta_norm, ""),
            ("scaled_delta_norm", "Scaled Delta Norm", raw.scaled_delta_norm, ""),
            ("relative_tol", "Relative Tolerance", raw.relative_tol, ""),
            ("residual_scale", "Residual Scale", raw.residual_scale, ""),
            ("solution_scale", "Solution Scale", raw.solution_scale, ""),
            ("damping_factor", "Damping Factor", raw.damping_factor, ""),
            ("max_electric_field", "Max Electric Field", raw.max_electric_field, "V/cm"),
            ("jacobian_condition_estimate", "Jacobian Condition", raw.jacobian_condition_estimate, ""),
            ("charge_neutrality_error", "Charge Neutrality Error", raw.charge_neutrality_error, "C/cm"),
            ("max_carrier_density", "Max Carrier Density", raw.max_carrier_density, "cm⁻³"),
            ("convergence_risk_score", "Convergence Risk", raw.convergence_risk_score, ""),
            ("mesh_quality_indicator", "Mesh Quality", raw.mesh_quality_indicator, ""),
            ("current_continuity_error", "Current Continuity Error", raw.current_continuity_error, ""),
        ]
        probes: list[UnifiedProbe] = []
        for name, label, value, unit in scalar_fields:
            probes.append(
                UnifiedProbe(
                    name=name,
                    label=label,
                    type="scalar",
                    unit=unit if unit else "",
                    value=value,
                    x=[float(raw.iteration)],
                    y=[float(value) if isinstance(value, (int, float)) else 0.0],
                    timestamp=ts,
                )
            )
        probes.extend([
            UnifiedProbe(
                name="convergence_status",
                label="Convergence Status",
                type="scalar",
                value=None,
                timestamp=ts,
            ),
            UnifiedProbe(
                name="stalled",
                label="Stalled",
                type="boolean",
                value=raw.stalled,
                timestamp=ts,
            ),
            UnifiedProbe(
                name="is_unphysical",
                label="Unphysical",
                type="boolean",
                value=raw.is_unphysical,
                timestamp=ts,
            ),
            UnifiedProbe(
                name="exp_clamped",
                label="Exp Clamped",
                type="boolean",
                value=raw.exp_clamped,
                timestamp=ts,
            ),
        ])
        if raw.failure_reason:
            probes.append(
                UnifiedProbe(
                    name="failure_reason",
                    label=f"Failure: {raw.failure_reason}",
                    type="scalar",
                    value=None,
                    timestamp=ts,
                )
            )
        if raw.recommended_numerical_action:
            probes.append(
                UnifiedProbe(
                    name="recommended_numerical_action",
                    label=f"Recommended: {raw.recommended_numerical_action}",
                    type="scalar",
                    value=None,
                    timestamp=ts,
                )
            )
        return probes

    def normalize_decision(self, raw: PnAgentDecision) -> UnifiedAgentDecision:
        action = _PN_ACTION_MAP.get(raw.action.value, UnifiedAction.CONTINUE)
        return UnifiedAgentDecision(
            action=action,
            reason=raw.reason,
            confidence=raw.confidence,
            suggested_params=raw.suggested_params,
            raw_action=raw.action.value,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _sweep_series(sweep: PnSweepResult | None) -> list[SweepSeries]:
        if not sweep or not sweep.points:
            return []
        vapp = [p.Vapp for p in sweep.points]
        series = [
            SweepSeries(
                name="W_vs_Vapp",
                label="Depletion Width vs Bias",
                unit="cm",
                x=vapp,
                y=[p.W or 0.0 for p in sweep.points],
                y_label="W (cm)",
            ),
            SweepSeries(
                name="Cj_vs_Vapp",
                label="Junction Capacitance vs Bias",
                unit="F/cm²",
                x=vapp,
                y=[p.Cj or 0.0 for p in sweep.points],
                y_label="Cj (F/cm²)",
            ),
            SweepSeries(
                name="Emax_vs_Vapp",
                label="Max Field vs Bias",
                unit="V/cm",
                x=vapp,
                y=[p.Emax or 0.0 for p in sweep.points],
                y_label="Emax (V/cm)",
            ),
        ]
        if any(p.J is not None for p in sweep.points):
            series.append(
                SweepSeries(
                    name="I_vs_Vapp",
                    label="Current Density vs Bias",
                    unit="A/cm²",
                    x=vapp,
                    y=[p.J or 0.0 for p in sweep.points],
                    y_label="J (A/cm²)",
                )
            )
        if any(p.Cj_diff is not None for p in sweep.points):
            series.append(
                SweepSeries(
                    name="C_vs_Vapp",
                    label="Differential Capacitance vs Bias",
                    unit="F/cm²",
                    x=vapp,
                    y=[p.Cj_diff or 0.0 for p in sweep.points],
                    y_label="C (F/cm²)",
                )
            )
        if any(p.M is not None for p in sweep.points):
            series.append(
                SweepSeries(
                    name="M_vs_Vapp",
                    label="Impact Ionization M vs Bias",
                    unit="",
                    x=vapp,
                    y=[p.M or 1.0 for p in sweep.points],
                    y_label="M",
                )
            )
        return series

    @staticmethod
    def _time_series(raw: PnTrialResult) -> list[TimeSeries]:
        if not raw.time_series:
            return []
        ts = [float(p.get("t", 0.0)) for p in raw.time_series]
        out: list[TimeSeries] = []
        if any("J" in p for p in raw.time_series):
            out.append(
                TimeSeries(
                    name="J_vs_t",
                    label="Terminal Current vs Time",
                    unit="A/cm²",
                    t=ts,
                    y=[float(p.get("J") or 0.0) for p in raw.time_series],
                )
            )
        if any("Vapp" in p for p in raw.time_series):
            out.append(
                TimeSeries(
                    name="Vapp_vs_t",
                    label="Applied Bias vs Time",
                    unit="V",
                    t=ts,
                    y=[float(p.get("Vapp") or 0.0) for p in raw.time_series],
                )
            )
        if any("psi_mid" in p for p in raw.time_series):
            out.append(
                TimeSeries(
                    name="psi_mid_vs_t",
                    label="Midpoint Potential vs Time",
                    unit="V",
                    t=ts,
                    y=[float(p.get("psi_mid") or 0.0) for p in raw.time_series],
                )
            )
        return out

    def normalize_result(
        self,
        run_id: str,
        raw: PnTrialResult,
        status: str = "completed",
        logs: list[str] | None = None,
        all_trials: list[PnTrialResult] | None = None,
    ) -> UnifiedRunResult:
        run_status_str = raw.run_status or derive_run_status(
            raw.solver_status,
            raw.validation,
            early_stopped=raw.early_stopped,
        )
        run_status = RunStatus(run_status_to_api(run_status_str))

        xs = [p.x for p in raw.profile] if raw.profile else []
        profiles: list[ProfileSeries] = []
        if raw.profile:
            profiles = [
                ProfileSeries(name="potential", label="Potential ψ(x)", unit="V", x=xs, y=[p.psi for p in raw.profile], x_label="x (cm)"),
                ProfileSeries(name="electric_field", label="Electric Field E(x)", unit="V/cm", x=xs, y=[p.E for p in raw.profile], x_label="x (cm)"),
                ProfileSeries(name="electron_density", label="Electron n(x)", unit="cm⁻³", x=xs, y=[p.n for p in raw.profile], x_label="x (cm)"),
                ProfileSeries(name="hole_density", label="Hole p(x)", unit="cm⁻³", x=xs, y=[p.p for p in raw.profile], x_label="x (cm)"),
                ProfileSeries(name="charge_density", label="Charge ρ(x)", unit="C/cm³", x=xs, y=[p.rho for p in raw.profile], x_label="x (cm)"),
            ]
        conv = [
            ConvergenceSeries(
                name="residual",
                label="Newton Residual (absolute)",
                unit="",
                x=[float(p.iteration) for p in raw.probes],
                y=[p.residual_norm for p in raw.probes],
                x_label="Iteration",
                y_label="Residual Norm",
            ),
            ConvergenceSeries(
                name="scaled_residual",
                label="Scaled Residual",
                unit="",
                x=[float(p.iteration) for p in raw.probes],
                y=[p.scaled_residual_norm for p in raw.probes],
                x_label="Iteration",
                y_label="Scaled Residual",
            ),
            ConvergenceSeries(
                name="scaled_delta",
                label="Scaled Newton Step",
                unit="",
                x=[float(p.iteration) for p in raw.probes],
                y=[p.scaled_delta_norm for p in raw.probes],
                x_label="Iteration",
                y_label="Scaled Delta",
            ),
        ]
        latest = raw.probes[-1] if raw.probes else None
        probes: list[UnifiedProbe] = self.normalize_probes(latest) if latest else []

        scalars: dict[str, ScalarMetric] = {}
        if raw.Vbi_numeric is not None:
            scalars["Vbi"] = ScalarMetric(value=raw.Vbi_numeric, unit="V", label="Built-in Potential")
        if raw.W_numeric is not None:
            scalars["W"] = ScalarMetric(value=raw.W_numeric, unit="cm", label="Depletion Width")
        if raw.W_psi_numeric is not None:
            scalars["W_psi"] = ScalarMetric(value=raw.W_psi_numeric, unit="cm", label="Depletion Width (ψ)")
        if raw.W_rho_numeric is not None:
            scalars["W_rho"] = ScalarMetric(value=raw.W_rho_numeric, unit="cm", label="Depletion Width (ρ)")
        if raw.Emax_numeric is not None:
            scalars["Emax"] = ScalarMetric(value=raw.Emax_numeric, unit="V/cm", label="Max Electric Field")
        if raw.Cj_estimate is not None:
            scalars["Cj"] = ScalarMetric(value=raw.Cj_estimate, unit="F/cm²", label="Junction Capacitance")
        if raw.J_terminal is not None:
            scalars["J"] = ScalarMetric(value=raw.J_terminal, unit="A/cm²", label="Terminal Current")
        if raw.M_ionization is not None:
            scalars["M_ionization"] = ScalarMetric(
                value=raw.M_ionization, unit="", label="Impact Ionization M"
            )
        scalars["breakdown_risk"] = ScalarMetric(
            value=1.0 if raw.breakdown_risk else 0.0,
            unit="",
            label="Breakdown Risk",
        )
        scalars["newton_iterations"] = ScalarMetric(value=float(raw.newton_iterations), unit="", label="Newton Iterations")
        if latest is not None:
            scalars["final_residual_norm"] = ScalarMetric(
                value=latest.residual_norm, unit="", label="Final Residual Norm"
            )
            scalars["final_scaled_residual_norm"] = ScalarMetric(
                value=latest.scaled_residual_norm, unit="", label="Final Scaled Residual"
            )
            scalars["final_delta_norm"] = ScalarMetric(
                value=latest.delta_norm, unit="", label="Final Delta Norm"
            )
            scalars["final_scaled_delta_norm"] = ScalarMetric(
                value=latest.scaled_delta_norm, unit="", label="Final Scaled Delta"
            )
            scalars["relative_tol"] = ScalarMetric(
                value=latest.relative_tol, unit="", label="Relative Tolerance"
            )

        convergence_summary: ConvergenceSummaryView | None = None
        if raw.convergence_summary is not None:
            cs = raw.convergence_summary
            convergence_summary = ConvergenceSummaryView(
                criterion=cs.criterion,
                relative_tol=cs.relative_tol,
                absolute_tol=cs.absolute_tol,
                residual_scale=cs.residual_scale,
                solution_scale=cs.solution_scale,
                final_residual_norm=cs.final_residual_norm,
                final_scaled_residual_norm=cs.final_scaled_residual_norm,
                final_delta_norm=cs.final_delta_norm,
                final_scaled_delta_norm=cs.final_scaled_delta_norm,
                criterion_met=cs.criterion_met,
                solver_warnings=cs.solver_warnings,
            )

        validation: dict[str, ValidationMetricView] | None = None
        validation_status: str | None = validation_status_for_api(raw.validation)
        validation_reason: str | None = None
        solver_status: str | None = raw.solver_status.value if raw.solver_status else None
        if raw.validation:
            validation_reason = raw.validation.reason or None
            if raw.validation.status in (
                ValidationStatus.ANALYTIC_PASSED,
                ValidationStatus.ANALYTIC_FAILED,
            ):
                validation = {}
                for key in ("Vbi", "W", "W_psi", "W_rho", "Emax"):
                    metric = getattr(raw.validation, key, None)
                    if metric:
                        validation[key] = ValidationMetricView(
                            numeric=metric.numeric,
                            analytic=metric.analytic,
                            rel_error=metric.rel_error,
                            passed=metric.passed,
                        )

        sweep = raw.sweep
        if all_trials:
            for trial in all_trials:
                if trial.sweep and trial.sweep.points:
                    sweep = trial.sweep
                    break

        trials_summary: list[TrialSummary] = []
        if all_trials and len(all_trials) > 1:
            for t in all_trials:
                t_run = RunStatus(run_status_to_api(t.run_status or derive_run_status(
                    t.solver_status, t.validation, early_stopped=t.early_stopped,
                )))
                trials_summary.append(
                    TrialSummary(
                        trial_index=t.trial_index,
                        status=t_run,
                        stop_reason=t.stop_reason,
                        early_stopped=t.early_stopped,
                        scalars={
                            k: ScalarMetric(value=v, unit="", label=k)
                            for k, v in {
                                "Vapp": t.input.Vapp,
                                "W": t.W_numeric or 0.0,
                                "Emax": t.Emax_numeric or 0.0,
                            }.items()
                        },
                    )
                )

        error_msg = None
        if run_status == RunStatus.FAILED:
            error_msg = raw.stop_reason or "simulation failed"
        elif run_status == RunStatus.COMPLETED_WITH_WARNING:
            error_msg = None

        return UnifiedRunResult(
            run_id=run_id,
            model_id=self.model_id,
            status=run_status,
            trial_index=raw.trial_index,
            scalars=scalars,
            profiles=profiles,
            time_series=self._time_series(raw),
            convergence=conv,
            sweep=self._sweep_series(sweep),
            probes=probes,
            decisions=[self.normalize_decision(d) for d in raw.decisions],
            logs=logs or [],
            validation=validation,
            solver_status=solver_status,
            validation_status=validation_status,
            validation_reason=validation_reason,
            run_status=run_status_str,
            convergence_summary=convergence_summary,
            trials=trials_summary,
            error=error_msg,
        )

    @staticmethod
    def build_config(raw: dict[str, Any], agent: str | None = None) -> PnRunConfig:
        flat = apply_agent_override(flatten_config(raw), agent)
        return PnRunConfig.model_validate(flat)
