export type RunStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'completed_with_warning'
  | 'failed'
  | 'early_stopped';

export type SolverStatusKind =
  | 'converged'
  | 'max_iter_reached'
  | 'not_converged'
  | 'failed_nan'
  | 'failed_unphysical'
  | 'stalled'
  | 'early_stopped'
  | 'analytic_complete';

export type ValidationStatusKind = 'passed' | 'failed' | 'unavailable' | 'numerical_only';

export type UnifiedAction =
  | 'continue'
  | 'early_stop'
  | 'adjust_params'
  | 'refine_mesh'
  | 'explain_failure'
  | 'recommend_next'
  | 'mark_infeasible';

export interface ParameterSchema {
  name: string;
  label: string;
  type: 'number' | 'integer' | 'select' | 'boolean' | 'string';
  unit?: string;
  default?: unknown;
  min?: number;
  max?: number;
  step?: number;
  group?: string;
  description?: string;
  options?: Array<{ value: string; label: string }>;
}

export interface ChartTabSchema {
  id: string;
  label: string;
  chart_type:
    | 'profiles'
    | 'profiles_combined'
    | 'profile_single'
    | 'time_series'
    | 'convergence'
    | 'overview'
    | 'sweep'
    | 'iv_curve'
    | 'line_profile'
    | 'optimization';
  series_names?: string[];
  log_scale?: boolean;
  viz_id?: string;
  viz_groups?: string[][];
}

export interface TreeNodeSchema {
  id: string;
  label: string;
  parameter_groups: string[];
}

export interface ModelDescriptor {
  model_id: string;
  model_name: string;
  category: string;
  dimension: string;
  description: string;
  parameters: ParameterSchema[];
  outputs: Array<{ name: string; label: string; chart_type: string; unit?: string }>;
  probes: Array<{ name: string; label: string; type: string; unit?: string }>;
  tree_nodes: TreeNodeSchema[];
  default_charts: ChartTabSchema[];
  default_config: Record<string, unknown>;
}

export interface ScalarMetric {
  value: number;
  unit: string;
  label: string;
}

export interface ProfileSeries {
  name: string;
  label: string;
  unit: string;
  x: number[];
  y: number[];
  x_label?: string;
}

export interface TimeSeries {
  name: string;
  label: string;
  unit: string;
  t: number[];
  y: number[];
}

export interface ConvergenceSeries {
  name: string;
  label: string;
  unit: string;
  x: number[];
  y: number[];
  x_label?: string;
  y_label?: string;
}

export interface SweepSeries {
  name: string;
  label: string;
  unit: string;
  x: number[];
  y: number[];
  x_label?: string;
  y_label?: string;
}

export interface UnifiedProbe {
  name: string;
  label: string;
  type: 'scalar' | 'series' | 'boolean';
  unit?: string;
  value?: number | boolean | null;
  x?: number[];
  y?: number[];
  timestamp?: string;
}

export interface UnifiedAgentDecision {
  action: UnifiedAction;
  reason: string;
  confidence: number;
  suggested_params?: Record<string, unknown> | null;
  raw_action?: string;
  timestamp?: string;
}

export interface TrialSummary {
  trial_index: number;
  status: RunStatus;
  stop_reason: string;
  early_stopped: boolean;
  scalars: Record<string, ScalarMetric>;
}

export interface ConvergenceSummary {
  criterion: string;
  relative_tol: number;
  absolute_tol?: number | null;
  residual_scale: number;
  solution_scale: number;
  final_residual_norm: number;
  final_scaled_residual_norm: number;
  final_delta_norm: number;
  final_scaled_delta_norm: number;
  criterion_met: string;
  solver_warnings?: string[];
}

export interface UnifiedRunResult {
  run_id: string;
  model_id: string;
  status: RunStatus;
  trial_index: number;
  scalars: Record<string, ScalarMetric>;
  profiles: ProfileSeries[];
  time_series: TimeSeries[];
  convergence: ConvergenceSeries[];
  sweep: SweepSeries[];
  probes: UnifiedProbe[];
  decisions: UnifiedAgentDecision[];
  logs: string[];
  validation?: Record<string, { numeric: number; analytic: number; rel_error: number; passed: boolean }>;
  solver_status?: SolverStatusKind | null;
  validation_status?: ValidationStatusKind | null;
  validation_reason?: string | null;
  run_status?: string | null;
  convergence_summary?: ConvergenceSummary | null;
  trials: TrialSummary[];
  error?: string | null;
}

export interface CreateRunRequest {
  project: Record<string, unknown>;
  active_study_id?: string | null;
  agent?: string;
  max_trials?: number;
}

export interface ProjectTemplateListItem {
  template_id: string;
  project_id: string;
  title: string;
  active_study_id?: string | null;
}

export interface CreateRunResponse {
  run_id: string;
  model_id: string;
  status: RunStatus;
}

export type ApiMode = 'mock' | 'live';

export type Workspace = 'simulation' | 'benchmark';

export type OutcomeKind = 'pass' | 'warning' | 'fail';

export type ValidationModeKind = 'analytic_abrupt' | 'numerical_only' | 'validation_unavailable';

export type DisplayCategory =
  | 'passed'
  | 'warning'
  | 'failed'
  | 'numerical_only'
  | 'validation_unavailable';

export interface BenchmarkReportListItem {
  run_id: string;
  timestamp: string;
  git_commit: string | null;
  benchmark_suite: string;
  output_dir: string;
  total: number;
  passed_count: number;
  warning_count: number;
  failed_count: number;
  total_runtime_s: number;
  overall_passed: boolean;
}

export interface BenchmarkEnvironment {
  python_version: string;
  platform: string;
  hostname: string | null;
}

export interface BenchmarkSummary {
  total: number;
  passed_count: number;
  warning_count: number;
  failed_count: number;
  total_runtime_s: number;
  overall_passed: boolean;
}

export interface BenchmarkCaseReport {
  case_id: string;
  config_path: string;
  reference_path: string;
  model_type: string;
  doping_type: string;
  validation_mode: ValidationModeKind;
  category: string;
  description: string;
  solver_status: string;
  validation_status: string | null;
  validation_status_display: string | null;
  run_status: string;
  outcome: OutcomeKind;
  display_category: DisplayCategory;
  key_metrics: Record<string, number | boolean | null>;
  reference_metrics: Record<string, number | boolean | null>;
  relative_errors: Record<string, number | null>;
  tolerances: Record<string, number>;
  checks: Record<string, boolean>;
  warnings: string[];
  failure_reason: string | null;
  runtime_s: number;
  stop_reason: string | null;
}

export interface BenchmarkReport {
  schema_version: string;
  run_id: string;
  timestamp: string;
  git_commit: string | null;
  benchmark_suite: string;
  autosim_version: string;
  output_dir: string;
  environment: BenchmarkEnvironment;
  summary: BenchmarkSummary;
  case_results: BenchmarkCaseReport[];
}

export interface SimApi {
  listProjectTemplates(): Promise<ProjectTemplateListItem[]>;
  getProjectTemplate(templateId: string): Promise<import('./project').SimulationProject>;
  getProjectTreeSchema(project?: import('./project').SimulationProject): Promise<import('./project').ModelTreeSchema>;
  getProjectParameters(
    project: import('./project').SimulationProject,
    treePath: string,
  ): Promise<import('./project').ProjectParameterSchemaResponse>;
  createRun(request: CreateRunRequest): Promise<CreateRunResponse>;
  getRun(runId: string): Promise<UnifiedRunResult>;
  subscribeRun(runId: string, handlers: StreamHandlers): () => void;
  listBenchmarkReports(): Promise<BenchmarkReportListItem[]>;
  getBenchmarkReport(runId: string): Promise<BenchmarkReport>;
  getBenchmarkReportMarkdown(runId: string): Promise<string>;
  runBenchmarkSuite(): Promise<BenchmarkRunResponse>;
}

export interface BenchmarkRunResponse {
  run_id: string;
  overall_passed: boolean;
  total: number;
  passed_count: number;
  warning_count: number;
  failed_count: number;
  total_runtime_s: number;
  output_dir: string;
}

export interface StreamHandlers {
  onProbe?: (probe: UnifiedProbe) => void;
  onDecision?: (decision: UnifiedAgentDecision) => void;
  onLog?: (message: string) => void;
  onStatus?: (status: RunStatus) => void;
  onComplete?: (result: UnifiedRunResult) => void;
  onError?: (error: string) => void;
}

export type { SimulationProject, ModelTreeSchema, ModelTreeNode, VisualizationRecipe } from './project';
