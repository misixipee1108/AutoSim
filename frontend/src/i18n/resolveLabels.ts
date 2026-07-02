/**
 * Centralized label resolution: English fallbacks from API/schema → localized strings.
 */

import type { ParameterSchema } from '../types';
import type { SimulationProject } from '../types/project';
import { t, tMetric, tModel, tModelOptionHelp, tRuntime } from './translations';

export type PhysicsModelId = 'pn_junction_1d' | 'falling_block';

const INTERFACE_TO_MODEL: Record<string, PhysicsModelId> = {
  semiconductor_1d_poisson: 'pn_junction_1d',
  semiconductor_1d_dd: 'pn_junction_1d',
  mechanics_0d_falling_body: 'falling_block',
};

/** Map full parameter path → model JSON param key. */
export function paramPathToI18nKey(path: string): string {
  if (path.endsWith('.junction_position')) return 'junction_position';
  if (path.includes('.segments.0.length')) return 'Lp';
  if (path.includes('.segments.1.length')) return 'Ln';
  if (path.endsWith('.material_id') || path.endsWith('.materials.0.material_id')) return 'material';
  if (path.endsWith('.temperature_k')) return 'temperature_k';
  if (path.endsWith('.doping.type')) return 'doping.type';
  if (path.endsWith('.doping.Na')) return 'Na';
  if (path.endsWith('.doping.Nd')) return 'Nd';
  if (path.endsWith('.model_type')) return 'model_type';
  if (path.endsWith('.Nx')) return 'Nx';
  if (path.endsWith('.junction_refinement.enabled')) return 'junction_refinement.enabled';
  if (path.endsWith('.junction_refinement.ratio')) return 'junction_refinement.ratio';
  if (path.endsWith('.junction_refinement.width_frac')) return 'junction_refinement.width_frac';
  if (path.endsWith('.parameters.Vapp')) return 'Vapp';
  if (path.endsWith('.relative_tol')) return 'tol';
  if (path.endsWith('.max_iter')) return 'max_iter';
  if (path.endsWith('.damping')) return 'damping';
  if (path.endsWith('.solver_id')) return 'solver.method';
  if (path.endsWith('.agent.backend')) return 'agent.backend';
  if (path.endsWith('.agent.probe_window')) return 'agent.probe_window';
  if (path.endsWith('.mass')) return 'mass';
  if (path.endsWith('.gravity')) return 'gravity';
  if (path.endsWith('.y0')) return 'y0';
  if (path.endsWith('.v0')) return 'v0';
  if (path.endsWith('.ground_y')) return 'ground_y';
  if (path.endsWith('.drag_model')) return 'drag_model';
  if (path.endsWith('.t_max')) return 't_max';
  if (path.endsWith('.dt')) return 'dt';
  if (path.endsWith('.probe_interval')) return 'probe_interval';
  const tail = path.split('.').pop() ?? path;
  return tail;
}

export function inferModelIdFromProject(project: SimulationProject | null): PhysicsModelId {
  if (!project) return 'pn_junction_1d';
  const ifaces = project.model.physics_interfaces as Array<{ interface_id?: string }> | undefined;
  const id = ifaces?.[0]?.interface_id ?? '';
  return INTERFACE_TO_MODEL[id] ?? 'pn_junction_1d';
}

export function inferModelIdFromRun(modelId: string, project?: SimulationProject | null): PhysicsModelId {
  if (modelId === 'pn_junction_1d' || modelId === 'falling_block') return modelId;
  if (modelId.includes('falling') || modelId.includes('fb')) return 'falling_block';
  return inferModelIdFromProject(project ?? null);
}

export function resolveParamLabel(
  modelId: PhysicsModelId,
  param: ParameterSchema,
): string {
  const key = paramPathToI18nKey(param.name);
  return tModel(modelId, `params.${key}.label`, param.label);
}

export function resolveParamDescription(
  modelId: PhysicsModelId,
  param: ParameterSchema,
): string {
  const key = paramPathToI18nKey(param.name);
  return tModel(modelId, `params.${key}.description`, param.description ?? '');
}

export function resolveParamOption(
  modelId: PhysicsModelId,
  param: ParameterSchema,
  value: string,
  fallback: string,
): string {
  const key = paramPathToI18nKey(param.name);
  return tModel(modelId, `params.${key}.options.${value}`, fallback);
}

export function resolveParamOptionHelp(
  modelId: PhysicsModelId,
  param: ParameterSchema,
  value: string,
  fallback: string,
): string {
  const key = paramPathToI18nKey(param.name);
  return tModelOptionHelp(modelId, key, value, fallback);
}

export function resolveParamGroup(modelId: PhysicsModelId, group: string | undefined): string {
  if (!group) return '';
  return tModel(modelId, `groups.${group}`, group);
}

const STUDY_LABEL_BY_RAW: Record<string, string> = {
  'Parameter Sweep': 'projectTree.studyLabels.parameterSweep',
  'Bias Sweep': 'projectTree.studyLabels.biasSweep',
  'Cv Sweep': 'projectTree.studyLabels.cvSweep',
  'C-V Sweep': 'projectTree.studyLabels.cvSweep',
  Optimization: 'projectTree.studyLabels.optimization',
  'Time Dependent': 'projectTree.studyLabels.timeDependent',
  'Time Dependent Fall': 'projectTree.studyLabels.timeDependentFall',
  'Stationary Equilibrium': 'projectTree.studyLabels.stationaryEquilibrium',
};

const STUDY_ID_SUFFIX: Record<string, string> = {
  study_parameter_sweep: 'projectTree.studyLabels.parameterSweep',
  study_bias_sweep: 'projectTree.studyLabels.biasSweep',
  study_cv_sweep: 'projectTree.studyLabels.cvSweep',
  study_optimization: 'projectTree.studyLabels.optimization',
  study_transient: 'projectTree.studyLabels.timeDependent',
  stat_equilibrium: 'projectTree.studyLabels.stationaryEquilibrium',
};

const STUDY_TYPE_KEYS: Record<string, string> = {
  stationary: 'projectTree.studyTypes.stationary',
  parameter_sweep: 'projectTree.studyTypes.parameter_sweep',
  bias_sweep: 'projectTree.studyTypes.bias_sweep',
  cv_sweep: 'projectTree.studyTypes.cv_sweep',
  optimization: 'projectTree.studyTypes.optimization',
  time_dependent: 'projectTree.studyTypes.time_dependent',
  transient: 'projectTree.studyTypes.transient',
};

const INTERFACE_LABEL_KEYS: Record<string, string> = {
  semiconductor_1d_poisson: 'projectTree.interfaces.semiconductor_1d_poisson',
  semiconductor_1d_dd: 'projectTree.interfaces.semiconductor_1d_dd',
  mechanics_0d_falling_body: 'projectTree.interfaces.mechanics_0d_falling_body',
};

export function resolveTreeLabel(
  nodeId: string,
  rawLabel: string,
  opts?: { studyType?: string; interfaceId?: string; physicsCategory?: string; parameterGroup?: string },
): string {
  const direct = t(`projectTree.${nodeId}`, undefined, '');
  if (direct && direct !== `projectTree.${nodeId}` && direct !== nodeId) return direct;

  const groupMatch = nodeId.match(/^model\.physics_interfaces\.[^.]+\.(\w+)$/);
  if (groupMatch) {
    const slug = groupMatch[1];
    const bySlug = t(`projectTree.group.${slug}`, undefined, '');
    if (bySlug && bySlug !== `projectTree.group.${slug}`) return bySlug;
    if (opts?.parameterGroup) {
      const byGroup = t(`projectTree.group.${opts.parameterGroup}`, undefined, '');
      if (byGroup && byGroup !== `projectTree.group.${opts.parameterGroup}`) return byGroup;
    }
  }

  const fieldMatch = nodeId.match(/^model\.physics_interfaces\.([^.]+)$/);
  if (fieldMatch && !fieldMatch[1].startsWith('template')) {
    const category = opts?.physicsCategory;
    if (category) {
      const byCategory = t(`projectTree.physicsField.${category}`, undefined, '');
      if (byCategory && byCategory !== `projectTree.physicsField.${category}`) return byCategory;
    }
  }

  if (nodeId.endsWith('.study_params')) {
    return t('projectTree.studyParams', undefined, rawLabel);
  }
  if (nodeId.endsWith('.solver_sequence')) {
    return t('projectTree.solverSequence', undefined, rawLabel);
  }
  if (nodeId.endsWith('.agent')) {
    return t('projectTree.studyAgent', undefined, rawLabel);
  }

  const studyMatch = nodeId.match(/^studies\.([^.]+)$/);
  if (studyMatch) {
    const studyId = studyMatch[1];
    const byId = STUDY_ID_SUFFIX[studyId];
    if (byId) return t(byId, undefined, rawLabel);
    const byRaw = STUDY_LABEL_BY_RAW[rawLabel];
    if (byRaw) return t(byRaw, undefined, rawLabel);
    if (opts?.studyType && STUDY_TYPE_KEYS[opts.studyType]) {
      return t(STUDY_TYPE_KEYS[opts.studyType], undefined, rawLabel);
    }
  }

  const ifaceMatch = nodeId.match(/^model\.physics_interfaces\.(.+)$/);
  if (ifaceMatch && opts?.interfaceId && INTERFACE_LABEL_KEYS[opts.interfaceId] && ifaceMatch[1].includes('template')) {
    return t(INTERFACE_LABEL_KEYS[opts.interfaceId], undefined, rawLabel);
  }

  const byRaw = STUDY_LABEL_BY_RAW[rawLabel];
  if (byRaw) return t(byRaw, undefined, rawLabel);

  return rawLabel;
}

const CHART_TAB_KEYS: Record<string, string> = {
  overview: 'charts.overview',
  profiles: 'charts.profiles',
  carriers: 'charts.carriers',
  convergence: 'charts.convergence',
  sweep: 'charts.sweep',
  cv: 'charts.cv_curve',
  cv_curve: 'charts.cv_curve',
  transient: 'charts.transient',
  optimization: 'charts.optimization',
  time_series: 'charts.time_series',
};

export function resolveChartTabLabel(tabId: string, rawLabel: string, modelId?: PhysicsModelId): string {
  const uiKey = CHART_TAB_KEYS[tabId];
  if (uiKey) {
    const uiVal = t(uiKey, undefined, '');
    if (uiVal && uiVal !== uiKey) return uiVal;
  }
  if (modelId) {
    const modelVal = tModel(modelId, `charts.${tabId}`, '');
    if (modelVal && modelVal !== `charts.${tabId}`) return modelVal;
  }
  return rawLabel;
}

export function resolveProbeLabel(
  modelId: PhysicsModelId,
  name: string,
  fallback: string,
): string {
  if (name.startsWith('failure_reason') || fallback.startsWith('Failure:')) {
    const code = fallback.replace(/^Failure:\s*/i, '').trim();
    return tRuntime(`failureReason.${code}`, resolveFailureReason(code, fallback));
  }
  if (name.startsWith('recommended_numerical_action') || fallback.startsWith('Recommended:')) {
    const code = fallback.replace(/^Recommended:\s*/i, '').trim();
    return tRuntime(`recommendedAction.${code}`, fallback);
  }
  const fromModel = tModel(modelId, `probes.${name}`, '');
  if (fromModel && fromModel !== `probes.${name}`) return fromModel;
  return fallback;
}

function resolveFailureReason(code: string, fallback: string): string {
  return tRuntime(`failureReason.${code}`, fallback);
}

const AXIS_ALIASES: Record<string, string> = {
  'x (cm)': 'axes.x_cm',
  'ψ (V)': 'axes.psi_V',
  'Vapp (V)': 'axes.Vapp_V',
  'Emax (V/cm)': 'axes.Emax_Vcm',
  'W (cm)': 'axes.W_cm',
  't (s)': 'axes.time_s',
  'Time (s)': 'axes.time_s',
  Iteration: 'axes.iteration',
  'relative_tol': 'axes.relative_tol',
  'Value': 'axes.value',
};

export function resolveAxisLabel(raw: string | undefined | null): string {
  if (!raw) return '';
  const key = AXIS_ALIASES[raw];
  if (key) return tRuntime(key, raw);
  return raw;
}

export function resolveEnum(ns: string, value: string): string {
  return tRuntime(`${ns}.${value}`, value);
}

export function resolveTemplateTitle(templateId: string, rawTitle: string): string {
  return t(`templates.${templateId}`, undefined, rawTitle);
}

export function resolveProjectTitle(
  projectId: string,
  rawTitle: string,
  modelId?: PhysicsModelId,
): string {
  const byId = t(`projectTitles.${projectId}`, undefined, '');
  if (byId && byId !== `projectTitles.${projectId}`) return byId;
  if (modelId) {
    const byModel = tModel(modelId, 'name', '');
    if (rawTitle.toLowerCase().includes('pn') && byModel) return `${byModel} — ${rawTitle.split('—').pop()?.trim() ?? rawTitle}`;
  }
  return rawTitle;
}

export function resolveValidationReason(reason: string): string {
  if (!reason) return reason;
  const exact = tRuntime(`validationReason.${reason}`, '');
  if (exact && exact !== `validationReason.${reason}`) return exact;
  for (const [pattern, key] of VALIDATION_REASON_PATTERNS) {
    if (pattern.test(reason)) return tRuntime(key, reason);
  }
  return reason;
}

const VALIDATION_REASON_PATTERNS: Array<[RegExp, string]> = [
  [/no analytic reference for model_type=drift_diffusion/i, 'validationReason.no_analytic_dd'],
  [/no analytic reference for doping\.type=/i, 'validationReason.no_analytic_doping'],
  [/no analytic reference for model_type=/i, 'validationReason.no_analytic_model'],
  [/Shockley validation requires/i, 'validationReason.shockley_ineligible'],
];

const AGENT_REASON_EXACT: Record<string, string> = {
  'NaN detected in Newton iteration': 'agentReason.nan_detected',
  'Negative carrier concentration detected': 'agentReason.negative_carrier',
  'Boltzmann exponent clamped; reduce damping or bias step': 'agentReason.exp_clamped',
  'Newton stalled during bias sweep; reduce bias step': 'agentReason.bias_stall',
  'Newton residual stalled; refine junction mesh': 'agentReason.newton_stalled',
  'Slow but progressing convergence': 'agentReason.slow_convergence',
  'Newton iteration progressing': 'agentReason.newton_progressing',
  'Approximate convergence; refine mesh for tighter scaled residual': 'agentReason.approx_convergence',
  'Simulation converged successfully': 'agentReason.converged_ok',
};

const AGENT_REASON_PATTERNS: Array<[RegExp, string]> = [
  [/^Electric field near breakdown limit/i, 'agentReason.breakdown_near'],
  [/^High convergence risk/i, 'agentReason.high_risk'],
  [/^Jacobian ill-conditioned/i, 'agentReason.jacobian_ill'],
  [/^Rules veto:/i, 'agentReason.rules_veto'],
];

export function resolveAgentReason(reason: string): string {
  if (!reason) return reason;
  const exactKey = AGENT_REASON_EXACT[reason];
  if (exactKey) return tRuntime(exactKey, reason);
  for (const [pattern, key] of AGENT_REASON_PATTERNS) {
    if (pattern.test(reason)) return tRuntime(key, reason);
  }
  return reason;
}

export function resolveActionRaw(action: string): string {
  return tRuntime(`actionRaw.${action}`, tRuntime(`action.${action}`, action));
}

export function resolveParamKey(key: string): string {
  return tRuntime(`paramKeys.${key}`, key);
}

export function resolveMetricKey(key: string, fallback?: string): string {
  return tMetric(key, fallback ?? key);
}

export function resolveStudyLabelFromProject(project: SimulationProject): string {
  const study = project.studies.find((s) => s.study_id === project.active_study_id) ?? project.studies[0];
  if (!study) return '';
  const studyId = String(study.study_id ?? '');
  const label = String((study as { label?: string }).label ?? studyId);
  const studyType = (study as { study_type?: string }).study_type;
  return resolveTreeLabel(`studies.${studyId}`, label, {
    studyType,
  });
}
