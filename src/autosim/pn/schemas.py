"""PN junction simulation schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from autosim.pn.convergence import ConvergenceSpec
from autosim.schemas import AgentBackend, IterationConfig


class PnAgentAction(str, Enum):
    CONTINUE = "continue"
    EARLY_STOP = "early_stop"
    ADJUST_DAMPING = "adjust_damping"
    REFINE_MESH = "refine_mesh"
    ADJUST_BIAS_STEP = "adjust_bias_step"
    CHANGE_INITIAL_GUESS = "change_initial_guess"
    MARK_AS_INFEASIBLE = "mark_as_infeasible"
    EXPLAIN_FAILURE = "explain_failure"
    RECOMMEND_NEXT_PARAMETERS = "recommend_next_parameters"
    SWITCH_SOLVER = "switch_solver"
    REDUCE_BIAS_STEP = "reduce_bias_step"
    INCREASE_DAMPING = "increase_damping"


class PnAgentConfig(BaseModel):
    backend: AgentBackend = AgentBackend.HYBRID
    probe_window: int = 10
    residual_stall_threshold: float = 1e-3
    jacobian_cond_max: float = 1e12
    exp_clamp_limit: float = 40.0


class BiasScanSpec(BaseModel):
    enabled: bool = False
    Vapp_min: float = -1.0
    Vapp_max: float = 0.5
    Vapp_step: float = 0.1
    Vapp_list: list[float] | None = None
    warm_start: bool = True
    continuation: bool = True


class JunctionRefinementSpec(BaseModel):
    enabled: bool = False
    ratio: float = 3.0
    width_frac: float = 0.1


class BoundarySpec(BaseModel):
    left_type: Literal["dirichlet", "neumann"] = "dirichlet"
    right_type: Literal["dirichlet", "neumann"] = "dirichlet"
    left_flux: float = 0.0
    right_flux: float = 0.0


class DopingSpec(BaseModel):
    type: Literal[
        "abrupt", "linear_graded", "gaussian", "piecewise", "erfc", "custom", "table"
    ] = "abrupt"
    Na: float | None = None
    Nd: float | None = None
    expression: str | None = None
    file: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class RecombinationSpec(BaseModel):
    enabled: bool = False
    srh: bool = True
    auger: bool = False
    radiative: bool = False
    tau_n: float = 1e-6
    tau_p: float = 1e-6
    n1: float = 1.0e10
    p1: float = 1.0e10


class TransientBiasSpec(BaseModel):
    enabled: bool = False
    t_max: float = 1e-9
    dt: float = 1e-11
    waveform: Literal["step", "pulse", "ramp"] = "step"
    Vapp_initial: float = 0.0
    Vapp_final: float = 0.5
    pulse_width: float = 1e-10
    pulse_start: float = 0.0


class CVScanSpec(BaseModel):
    enabled: bool = False
    delta_V: float = 1e-3
    Vapp_min: float = -1.0
    Vapp_max: float = 0.0
    Vapp_step: float = 0.05


class BreakdownSpec(BaseModel):
    enabled: bool = True
    E_crit: float = 3.0e5
    alpha_model: Literal["chynoweth", "none"] = "chynoweth"
    alpha_n: float = 7.03e5
    alpha_p: float = 1.582e6
    alpha_exp: float = 1.0


class OutputsSpec(BaseModel):
    cv_sweep: bool = False
    iv_sweep: bool = False
    transient: bool = False


class SolverSpec(BaseModel):
    tol: float = 1e-6
    max_iter: int = 100
    damping: float = 1.0
    exp_clamp: float = 40.0
    method: Literal["newton", "damped_newton", "newton_line_search"] = "damped_newton"
    linear_backend: Literal["direct", "iterative"] = "direct"
    checkpoint_dir: str | None = None
    adaptive_damping: bool = False
    convergence: ConvergenceSpec = Field(default_factory=ConvergenceSpec)


class MaterialConfigSpec(BaseModel):
    name: str = "Si"
    temperature_k: float = 300.0
    ref: str | None = None


class GeometrySpec(BaseModel):
    Lp: float = 2e-4
    Ln: float = 2e-4
    xj: float = 0.0
    L: float | None = None


class BiasConfigSpec(BaseModel):
    Vapp: float = 0.0
    scan: BiasScanSpec = Field(default_factory=BiasScanSpec)


class MeshConfigSpec(BaseModel):
    Nx: int = 200
    junction_refinement: JunctionRefinementSpec = Field(default_factory=JunctionRefinementSpec)


class PnDesignVarSpec(BaseModel):
    name: str
    min: float
    max: float
    type: Literal["number", "integer"] = "number"


class PnObjectiveSpec(BaseModel):
    name: str
    target: Literal["min", "max", "range"] = "min"
    constraint: str | None = None
    min: float | None = None
    max: float | None = None


class PnOptimizationSpec(BaseModel):
    enabled: bool = False
    design_vars: list[PnDesignVarSpec] = Field(default_factory=list)
    objectives: list[PnObjectiveSpec] = Field(default_factory=list)
    max_trials: int = 20
    method: Literal["random", "grid", "optuna"] = "random"


class PnSimInput(BaseModel):
    model_type: Literal["poisson", "depletion", "drift_diffusion", "transient_dd"] = "poisson"
    material: str = "Si"
    temperature_k: float = 300.0
    Na: float = 1e18
    Nd: float = 1e16
    Lp: float = 2e-4
    Ln: float = 2e-4
    xj: float = 0.0
    Nx: int = 200
    boundary: BoundarySpec = Field(default_factory=BoundarySpec)
    Vapp: float = 0.0
    tol: float = 1e-6
    max_iter: int = 100
    damping: float = 1.0
    exp_clamp: float = 40.0
    rho_threshold_frac: float = 0.05
    psi_threshold_frac: float = 1e-3
    doping: DopingSpec | None = None
    solver: SolverSpec = Field(default_factory=SolverSpec)
    bias_scan: BiasScanSpec = Field(default_factory=BiasScanSpec)
    cv_scan: CVScanSpec = Field(default_factory=CVScanSpec)
    transient: TransientBiasSpec = Field(default_factory=TransientBiasSpec)
    recombination: RecombinationSpec = Field(default_factory=RecombinationSpec)
    breakdown: BreakdownSpec = Field(default_factory=BreakdownSpec)
    junction_refinement: JunctionRefinementSpec = Field(default_factory=JunctionRefinementSpec)
    optimization: PnOptimizationSpec = Field(default_factory=PnOptimizationSpec)
    agent: PnAgentConfig = Field(default_factory=PnAgentConfig)
    iteration: IterationConfig = Field(default_factory=IterationConfig)
    sources: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    probes: list[str] = Field(default_factory=list)

    def model_copy_with_params(self, params: dict[str, Any]) -> PnSimInput:
        data = self.model_dump()
        for key, value in params.items():
            if key in data and key not in (
                "agent", "iteration", "sources", "references", "bias_scan",
                "junction_refinement", "optimization", "doping", "solver",
            ):
                data[key] = value
            elif key == "agent" and isinstance(value, dict):
                data["agent"] = {**data.get("agent", {}), **value}
            elif key == "junction_refinement" and isinstance(value, dict):
                data["junction_refinement"] = {
                    **data.get("junction_refinement", {}), **value
                }
            elif key == "solver" and isinstance(value, dict):
                data["solver"] = {**data.get("solver", {}), **value}
            elif key == "doping" and isinstance(value, dict):
                data["doping"] = {**data.get("doping", {}), **value}
        return PnSimInput.model_validate(data)


class ConvergenceSummary(BaseModel):
    criterion: str = "both"
    relative_tol: float = 1e-4
    absolute_tol: float | None = None
    residual_scale: float = 1.0
    solution_scale: float = 1.0
    final_residual_norm: float = 0.0
    final_scaled_residual_norm: float = 0.0
    final_delta_norm: float = 0.0
    final_scaled_delta_norm: float = 0.0
    criterion_met: str = "none"
    solver_warnings: list[str] = Field(default_factory=list)


class PnNewtonProbe(BaseModel):
    iteration: int
    residual_norm: float
    residual_reduction_rate: float
    delta_norm: float
    scaled_residual_norm: float = 0.0
    scaled_delta_norm: float = 0.0
    residual_scale: float = 1.0
    solution_scale: float = 1.0
    relative_tol: float = 1e-4
    convergence_criterion: str = "both"
    criterion_met: str = "none"
    damping_factor: float
    jacobian_condition_estimate: float
    max_psi: float
    min_psi: float
    max_electric_field: float
    max_carrier_density: float
    min_n: float
    min_p: float
    charge_neutrality_error: float
    is_nan: bool
    is_unphysical: bool
    exp_clamped: bool
    stalled: bool
    convergence_status: str
    failure_reason: str = ""
    convergence_risk_score: float = 0.0
    mesh_quality_indicator: float = 1.0
    current_continuity_error: float = 0.0
    gummel_outer_iter: int = 0
    poisson_sub_iter: int = 0
    carrier_update_norm: float = 0.0


class PnAgentDecision(BaseModel):
    action: PnAgentAction
    reason: str
    confidence: float = 1.0
    suggested_params: dict[str, Any] | None = None


class ProfilePoint(BaseModel):
    x: float
    psi: float
    E: float
    n: float
    p: float
    rho: float


class ValidationMetric(BaseModel):
    numeric: float
    analytic: float
    rel_error: float
    passed: bool


class ValidationStatus(str, Enum):
    ANALYTIC_PASSED = "analytic_passed"
    ANALYTIC_FAILED = "analytic_failed"
    UNAVAILABLE = "unavailable"
    NUMERICAL_ONLY = "numerical_only"


class SolverStatus(str, Enum):
    CONVERGED = "converged"
    MAX_ITER_REACHED = "max_iter_reached"
    NOT_CONVERGED = "not_converged"
    FAILED_NAN = "failed_nan"
    FAILED_UNPHYSICAL = "failed_unphysical"
    STALLED = "stalled"
    EARLY_STOPPED = "early_stopped"
    ANALYTIC_COMPLETE = "analytic_complete"


class PnValidationReport(BaseModel):
    status: ValidationStatus = ValidationStatus.UNAVAILABLE
    reason: str = ""
    Vbi: ValidationMetric | None = None
    W: ValidationMetric | None = None
    W_psi: ValidationMetric | None = None
    W_rho: ValidationMetric | None = None
    Emax: ValidationMetric | None = None
    all_passed: bool = False


class PnSweepPoint(BaseModel):
    Vapp: float
    W: float | None = None
    W_psi: float | None = None
    W_rho: float | None = None
    Cj: float | None = None
    Cj_diff: float | None = None
    Emax: float | None = None
    Vbi: float | None = None
    J: float | None = None
    M: float | None = None
    breakdown_risk: bool = False
    converged: bool = False
    newton_iterations: int = 0


class PnSweepResult(BaseModel):
    points: list[PnSweepPoint] = Field(default_factory=list)
    all_converged: bool = False


class PnTrialResult(BaseModel):
    trial_index: int = 0
    input: PnSimInput
    profile: list[ProfilePoint] = Field(default_factory=list)
    probes: list[PnNewtonProbe] = Field(default_factory=list)
    decisions: list[PnAgentDecision] = Field(default_factory=list)
    Vbi_numeric: float | None = None
    W_numeric: float | None = None
    W_psi_numeric: float | None = None
    W_rho_numeric: float | None = None
    Emax_numeric: float | None = None
    Cj_estimate: float | None = None
    Cj_method: str = "W_rho"
    J_terminal: float | None = None
    M_ionization: float | None = None
    breakdown_risk: bool = False
    R_max: float | None = None
    sweep: PnSweepResult | None = None
    time_series: list[dict[str, Any]] = Field(default_factory=list)
    newton_iterations: int = 0
    converged: bool = False
    early_stopped: bool = False
    stop_reason: str = "completed"
    solver_status: SolverStatus = SolverStatus.NOT_CONVERGED
    run_status: str = "failed"
    validation: PnValidationReport | None = None
    convergence_summary: ConvergenceSummary | None = None
    model_type: str = "poisson"


class PnRunConfig(BaseModel):
    model_type: Literal["poisson", "depletion", "drift_diffusion", "transient_dd"] = "poisson"
    material: str | None = None
    temperature_k: float | None = None
    Na: float | None = None
    Nd: float | None = None
    Lp: float | None = None
    Ln: float | None = None
    Nx: int | None = None
    Vapp: float | None = None
    tol: float | None = None
    max_iter: int | None = None
    damping: float | None = None
    exp_clamp: float | None = None
    rho_threshold_frac: float | None = None
    psi_threshold_frac: float | None = None
    doping: DopingSpec | None = None
    solver: SolverSpec | None = None
    geometry: GeometrySpec | None = None
    mesh: MeshConfigSpec | None = None
    bias: BiasConfigSpec | None = None
    material_cfg: MaterialConfigSpec | None = Field(default=None, alias="material_block")
    boundary: BoundarySpec = Field(default_factory=BoundarySpec)
    bias_scan: BiasScanSpec = Field(default_factory=BiasScanSpec)
    cv_scan: CVScanSpec = Field(default_factory=CVScanSpec)
    transient: TransientBiasSpec = Field(default_factory=TransientBiasSpec)
    recombination: RecombinationSpec = Field(default_factory=RecombinationSpec)
    breakdown: BreakdownSpec = Field(default_factory=BreakdownSpec)
    junction_refinement: JunctionRefinementSpec = Field(default_factory=JunctionRefinementSpec)
    optimization: PnOptimizationSpec = Field(default_factory=PnOptimizationSpec)
    agent: PnAgentConfig = Field(default_factory=PnAgentConfig)
    iteration: IterationConfig = Field(default_factory=IterationConfig)
    sources: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    probes: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def normalize_structured(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        # Structured nested config → flat fields
        if "geometry" in d and isinstance(d["geometry"], dict):
            g = d["geometry"]
            d.setdefault("Lp", g.get("Lp"))
            d.setdefault("Ln", g.get("Ln"))
            d.setdefault("xj", g.get("xj", 0.0))
        if "mesh" in d and isinstance(d["mesh"], dict):
            m = d["mesh"]
            d.setdefault("Nx", m.get("Nx"))
            if "junction_refinement" in m:
                d["junction_refinement"] = m["junction_refinement"]
        if "bias" in d and isinstance(d["bias"], dict):
            b = d["bias"]
            d.setdefault("Vapp", b.get("Vapp"))
            if "scan" in b:
                d["bias_scan"] = b["scan"]
            if "transient" in b:
                d["transient"] = b["transient"]
        for key in ("cv_scan", "transient", "recombination", "breakdown", "boundary"):
            if key in d and isinstance(d[key], dict):
                pass
        if "material" in d and isinstance(d["material"], dict):
            mc = d["material"]
            d.setdefault("material", mc.get("name", "Si"))
            d.setdefault("temperature_k", mc.get("temperature_k", 300.0))
            refs = mc.get("ref")
            if refs:
                d.setdefault("references", []).append(str(refs))
        if "solver" in d and isinstance(d["solver"], dict):
            s = d["solver"]
            for k in ("tol", "max_iter", "damping", "exp_clamp", "method"):
                if k in s:
                    d.setdefault(k if k != "method" else "solver_method", s[k])
        refs = d.get("references") or d.get("sources")
        if refs and not d.get("sources"):
            d["sources"] = list(refs) if isinstance(refs, list) else [refs]
        return d

    def to_sim_input(self) -> PnSimInput:
        solver = self.solver or SolverSpec()
        flat = {
            "model_type": self.model_type,
            "material": self.material or "Si",
            "temperature_k": self.temperature_k if self.temperature_k is not None else 300.0,
            "Na": self.Na if self.Na is not None else 1e18,
            "Nd": self.Nd if self.Nd is not None else 1e16,
            "Lp": self.Lp if self.Lp is not None else 2e-4,
            "Ln": self.Ln if self.Ln is not None else 2e-4,
            "xj": self.geometry.xj if self.geometry else 0.0,
            "Nx": self.Nx if self.Nx is not None else 200,
            "boundary": self.boundary.model_dump(),
            "Vapp": self.Vapp if self.Vapp is not None else 0.0,
            "tol": self.tol if self.tol is not None else solver.tol,
            "max_iter": self.max_iter if self.max_iter is not None else solver.max_iter,
            "damping": self.damping if self.damping is not None else solver.damping,
            "exp_clamp": self.exp_clamp if self.exp_clamp is not None else solver.exp_clamp,
            "rho_threshold_frac": self.rho_threshold_frac if self.rho_threshold_frac is not None else 0.05,
            "psi_threshold_frac": self.psi_threshold_frac if self.psi_threshold_frac is not None else 1e-3,
            "doping": self.doping.model_dump() if self.doping else None,
            "solver": solver.model_dump(),
            "bias_scan": self.bias_scan.model_dump(),
            "cv_scan": self.cv_scan.model_dump(),
            "transient": self.transient.model_dump(),
            "recombination": self.recombination.model_dump(),
            "breakdown": self.breakdown.model_dump(),
            "junction_refinement": self.junction_refinement.model_dump(),
            "optimization": self.optimization.model_dump(),
            "agent": self.agent.model_dump(),
            "iteration": self.iteration.model_dump(),
            "sources": self.sources,
            "references": self.references or self.sources,
            "outputs": self.outputs,
            "probes": self.probes,
        }
        return PnSimInput.model_validate(flat)
