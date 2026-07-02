"""Unified API schemas for multi-model frontend compatibility."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNING = "completed_with_warning"
    FAILED = "failed"
    EARLY_STOPPED = "early_stopped"


class UnifiedAction(str, Enum):
    CONTINUE = "continue"
    EARLY_STOP = "early_stop"
    ADJUST_PARAMS = "adjust_params"
    REFINE_MESH = "refine_mesh"
    EXPLAIN_FAILURE = "explain_failure"
    RECOMMEND_NEXT = "recommend_next"
    MARK_INFEASIBLE = "mark_infeasible"


class ParameterSchema(BaseModel):
    name: str
    label: str
    type: Literal["number", "integer", "select", "boolean", "string"] = "number"
    unit: str = ""
    default: Any = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    group: str = "General"
    description: str = ""
    options: list[dict[str, str]] | None = None


class OutputSchema(BaseModel):
    name: str
    label: str
    chart_type: Literal["line_profile", "time_series", "convergence", "scalar", "sweep", "optimization"] = "line_profile"
    x: str = ""
    y: str = ""
    unit: str = ""
    x_label: str = ""
    y_label: str = ""


class ProbeSchema(BaseModel):
    name: str
    label: str
    type: Literal["scalar", "series", "boolean"] = "scalar"
    unit: str = ""
    x_label: str = ""
    y_label: str = ""


class TreeNodeSchema(BaseModel):
    id: str
    label: str
    parameter_groups: list[str] = Field(default_factory=list)


class ChartTabSchema(BaseModel):
    id: str
    label: str
    chart_type: Literal["profiles", "time_series", "convergence", "overview", "sweep", "optimization"] = "profiles"
    series_names: list[str] = Field(default_factory=list)


class ModelDescriptor(BaseModel):
    model_id: str
    model_name: str
    category: str
    dimension: Literal["0D", "1D", "2D", "3D"] = "1D"
    description: str = ""
    parameters: list[ParameterSchema] = Field(default_factory=list)
    outputs: list[OutputSchema] = Field(default_factory=list)
    probes: list[ProbeSchema] = Field(default_factory=list)
    tree_nodes: list[TreeNodeSchema] = Field(default_factory=list)
    default_charts: list[ChartTabSchema] = Field(default_factory=list)
    default_config: dict[str, Any] = Field(default_factory=dict)


class ScalarMetric(BaseModel):
    value: float
    unit: str = ""
    label: str = ""


class ProfileSeries(BaseModel):
    name: str
    label: str
    unit: str = ""
    x: list[float] = Field(default_factory=list)
    y: list[float] = Field(default_factory=list)
    x_label: str = ""


class TimeSeries(BaseModel):
    name: str
    label: str
    unit: str = ""
    t: list[float] = Field(default_factory=list)
    y: list[float] = Field(default_factory=list)


class ConvergenceSeries(BaseModel):
    name: str
    label: str
    unit: str = ""
    x: list[float] = Field(default_factory=list)
    y: list[float] = Field(default_factory=list)
    x_label: str = ""
    y_label: str = ""


class SweepSeries(BaseModel):
    name: str
    label: str
    unit: str = ""
    x: list[float] = Field(default_factory=list)
    y: list[float] = Field(default_factory=list)
    x_label: str = "Vapp (V)"
    y_label: str = ""


class UnifiedProbe(BaseModel):
    name: str
    label: str
    type: Literal["scalar", "series", "boolean"] = "scalar"
    unit: str = ""
    value: float | bool | None = None
    x: list[float] = Field(default_factory=list)
    y: list[float] = Field(default_factory=list)
    timestamp: str = ""


class UnifiedAgentDecision(BaseModel):
    action: UnifiedAction
    reason: str = ""
    confidence: float = 1.0
    suggested_params: dict[str, Any] | None = None
    raw_action: str = ""
    timestamp: str = ""


class ValidationMetricView(BaseModel):
    numeric: float
    analytic: float
    rel_error: float
    passed: bool = False


class ConvergenceSummaryView(BaseModel):
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


class TrialSummary(BaseModel):
    trial_index: int
    status: RunStatus
    stop_reason: str = ""
    early_stopped: bool = False
    scalars: dict[str, ScalarMetric] = Field(default_factory=dict)


class UnifiedRunResult(BaseModel):
    run_id: str
    model_id: str
    status: RunStatus = RunStatus.PENDING
    trial_index: int = 0
    scalars: dict[str, ScalarMetric] = Field(default_factory=dict)
    profiles: list[ProfileSeries] = Field(default_factory=list)
    time_series: list[TimeSeries] = Field(default_factory=list)
    convergence: list[ConvergenceSeries] = Field(default_factory=list)
    sweep: list[SweepSeries] = Field(default_factory=list)
    probes: list[UnifiedProbe] = Field(default_factory=list)
    decisions: list[UnifiedAgentDecision] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    validation: dict[str, ValidationMetricView] | None = None
    solver_status: str | None = None
    validation_status: str | None = None
    validation_reason: str | None = None
    run_status: str | None = None
    convergence_summary: ConvergenceSummaryView | None = None
    trials: list[TrialSummary] = Field(default_factory=list)
    error: str | None = None


class CreateRunRequest(BaseModel):
    model_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    project: dict[str, Any] | None = None
    active_study_id: str | None = None
    agent: str | None = None
    max_trials: int = 1


class ModelTreeSchemaResponse(BaseModel):
    schema_version: str = "2.0"
    roots: list[dict[str, Any]] = Field(default_factory=list)


class PhysicsInterfaceListItem(BaseModel):
    interface_id: str
    name: str
    category: str
    dimension: str
    governing_equations: list[str] = Field(default_factory=list)


class ProjectTemplateListItem(BaseModel):
    template_id: str
    project_id: str
    title: str
    active_study_id: str | None = None


class ProjectParameterSchemaResponse(BaseModel):
    tree_path: str
    parameters: list[ParameterSchema] = Field(default_factory=list)


class CreateRunResponse(BaseModel):
    run_id: str
    model_id: str
    status: RunStatus


class StreamEvent(BaseModel):
    event: Literal["probe", "decision", "log", "status", "complete", "error"]
    data: dict[str, Any] = Field(default_factory=dict)


DisplayCategoryKind = Literal[
    "passed",
    "warning",
    "failed",
    "numerical_only",
    "validation_unavailable",
]


class BenchmarkReportListItem(BaseModel):
    run_id: str
    timestamp: str
    git_commit: str | None = None
    benchmark_suite: str = "pn"
    output_dir: str = ""
    total: int = 0
    passed_count: int = 0
    warning_count: int = 0
    failed_count: int = 0
    total_runtime_s: float = 0.0
    overall_passed: bool = False


class BenchmarkCaseReportEnriched(BaseModel):
    case_id: str
    config_path: str = ""
    reference_path: str = ""
    model_type: str
    doping_type: str = "abrupt"
    validation_mode: Literal["analytic_abrupt", "numerical_only", "validation_unavailable"] = "analytic_abrupt"
    category: str = ""
    description: str = ""
    solver_status: str
    validation_status: str | None = None
    validation_status_display: str | None = None
    run_status: str
    outcome: Literal["pass", "warning", "fail"]
    display_category: DisplayCategoryKind
    key_metrics: dict[str, float | bool | int | None] = Field(default_factory=dict)
    reference_metrics: dict[str, float | bool | int | None] = Field(default_factory=dict)
    relative_errors: dict[str, float | None] = Field(default_factory=dict)
    tolerances: dict[str, float] = Field(default_factory=dict)
    checks: dict[str, bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    failure_reason: str | None = None
    runtime_s: float = 0.0
    stop_reason: str | None = None


class BenchmarkEnvironmentView(BaseModel):
    python_version: str
    platform: str
    hostname: str | None = None


class BenchmarkSummaryView(BaseModel):
    total: int
    passed_count: int
    warning_count: int
    failed_count: int
    total_runtime_s: float
    overall_passed: bool


class BenchmarkReportEnriched(BaseModel):
    schema_version: str = "1.0"
    run_id: str
    timestamp: str
    git_commit: str | None = None
    benchmark_suite: str = "pn"
    autosim_version: str = ""
    output_dir: str = ""
    environment: BenchmarkEnvironmentView
    summary: BenchmarkSummaryView
    case_results: list[BenchmarkCaseReportEnriched] = Field(default_factory=list)
