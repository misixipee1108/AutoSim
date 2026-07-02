/** Client-side parameter schema resolution for project tree nodes (mock + offline). */

import type { ChartTabSchema, ParameterSchema, SimulationProject } from '../types';
import { resolvePhysicsInterfaceParameters } from '../config/physicsInterfaceSchemas';
import { parsePhysicsInterfaceTreePath } from '../config/physicsTreeLabels';

function segmentLength(project: SimulationProject, side: string): number {
  const segments = (project.model.geometry as { segments?: Array<{ name: string; length: number }> })?.segments ?? [];
  for (const seg of segments) {
    if (seg.name.toLowerCase().includes(side)) return seg.length;
  }
  return 2e-4;
}

export function resolveProjectParameters(
  project: SimulationProject,
  treePath: string,
): ParameterSchema[] {
  if (treePath === 'model.geometry') {
    const geo = project.model.geometry as { junction_position?: number };
    return [
      {
        name: 'model.geometry.junction_position',
        label: 'Junction Position',
        type: 'number',
        unit: 'cm',
        default: geo.junction_position ?? 0,
        group: 'Geometry',
      },
      {
        name: 'model.geometry.segments.0.length',
        label: 'P-side Length',
        type: 'number',
        unit: 'cm',
        default: segmentLength(project, 'p'),
        group: 'Geometry',
      },
      {
        name: 'model.geometry.segments.1.length',
        label: 'N-side Length',
        type: 'number',
        unit: 'cm',
        default: segmentLength(project, 'n'),
        group: 'Geometry',
      },
    ];
  }

  if (treePath === 'model.mesh') {
    const mesh = project.model.mesh as {
      Nx?: number;
      junction_refinement?: { enabled?: boolean; ratio?: number; width_frac?: number };
    };
    const jref = mesh.junction_refinement ?? {};
    return [
      { name: 'model.mesh.Nx', label: 'Grid Points', type: 'integer', default: mesh.Nx ?? 400, min: 20, max: 5000, group: 'Mesh' },
      { name: 'model.mesh.junction_refinement.enabled', label: 'Junction Refinement', type: 'boolean', default: jref.enabled ?? false, group: 'Mesh' },
      { name: 'model.mesh.junction_refinement.ratio', label: 'Refinement Ratio', type: 'number', default: jref.ratio ?? 3, min: 1.1, max: 10, group: 'Mesh' },
      { name: 'model.mesh.junction_refinement.width_frac', label: 'Junction Zone Fraction', type: 'number', default: jref.width_frac ?? 0.1, min: 0.01, max: 0.5, group: 'Mesh' },
    ];
  }

  if (treePath === 'model.material') {
    const mats = (project.model.materials as Array<{ material_id?: string; temperature_k?: number }>) ?? [];
    const mat = mats[0] ?? {};
    return [
      {
        name: 'model.materials.0.material_id',
        label: 'Material',
        type: 'select',
        default: mat.material_id ?? 'Si',
        group: 'Material',
        options: [
          { value: 'Si', label: 'Silicon (Si)' },
          { value: 'Ge', label: 'Germanium (Ge)' },
          { value: 'GaAs', label: 'GaAs' },
        ],
      },
      {
        name: 'model.materials.0.temperature_k',
        label: 'Temperature',
        type: 'number',
        unit: 'K',
        default: mat.temperature_k ?? 300,
        min: 100,
        max: 500,
        group: 'Material',
      },
    ];
  }

  if (treePath.startsWith('model.physics_interfaces.')) {
    const { instanceId, groupName } = parsePhysicsInterfaceTreePath(treePath);
    if (!instanceId) return [];
    return resolvePhysicsInterfaceParameters(project, instanceId, getProjectValue, groupName ?? undefined);
  }

  if (treePath.includes('.study_params')) {
    const studyId = treePath.split('.')[1];
    const studies = project.studies as Array<{ study_id: string; parameters?: Record<string, unknown> }>;
    const study = studies.find((s) => s.study_id === studyId);
    return [
      {
        name: `studies.${studyId}.parameters.Vapp`,
        label: 'Applied Bias',
        type: 'number',
        unit: 'V',
        default: Number(study?.parameters?.Vapp ?? 0),
        min: -5,
        max: 5,
        group: 'Study',
      },
    ];
  }

  if (treePath.includes('.solver_sequence')) {
    const studyId = treePath.split('.')[1];
    const prefix = `studies.${studyId}.solver_sequence.0.settings`;
    return [
      { name: `${prefix}.relative_tol`, label: 'Relative Tolerance', type: 'number', default: 1e-4, min: 1e-10, max: 1e-2, group: 'Solver' },
      { name: `${prefix}.max_iter`, label: 'Max Iterations', type: 'integer', default: 200, min: 10, max: 1000, group: 'Solver' },
      { name: `${prefix}.damping`, label: 'Damping Factor', type: 'number', default: 0.5, min: 0.01, max: 1, group: 'Solver' },
      {
        name: `studies.${studyId}.solver_sequence.0.solver_id`,
        label: 'Nonlinear Solver',
        type: 'select',
        default: 'damped_newton',
        group: 'Solver',
        options: [
          { value: 'newton', label: 'Newton' },
          { value: 'damped_newton', label: 'Damped Newton' },
          { value: 'newton_line_search', label: 'Newton + Line Search' },
        ],
      },
    ];
  }

  if (treePath.includes('.agent')) {
    const studyId = treePath.split('.')[1];
    return [
      {
        name: `studies.${studyId}.agent.backend`,
        label: 'Agent Backend',
        type: 'select',
        default: 'rules',
        group: 'Agent',
        options: [
          { value: 'rules', label: 'Rules Only' },
          { value: 'deepseek', label: 'DeepSeek LLM' },
          { value: 'hybrid', label: 'Hybrid' },
        ],
      },
    ];
  }

  return [];
}

/** Resolve array segment: numeric index, study_id, or physics instance_id. */
function resolveArraySegment(arr: unknown[], part: string): unknown {
  const numericIdx = parseInt(part, 10);
  if (!Number.isNaN(numericIdx) && numericIdx >= 0 && numericIdx < arr.length) {
    return arr[numericIdx];
  }
  const sample = arr[0];
  if (sample && typeof sample === 'object') {
    if ('study_id' in sample) {
      return arr.find((item) => (item as { study_id?: string }).study_id === part);
    }
    if ('instance_id' in sample) {
      return arr.find((item) => (item as { instance_id?: string }).instance_id === part);
    }
  }
  return undefined;
}

/** Resolve array index for mutation (returns -1 if not found). */
function resolveArrayIndex(arr: unknown[], part: string): number {
  const numericIdx = parseInt(part, 10);
  if (!Number.isNaN(numericIdx) && numericIdx >= 0 && numericIdx < arr.length) {
    return numericIdx;
  }
  const sample = arr[0];
  if (sample && typeof sample === 'object') {
    if ('study_id' in sample) {
      return arr.findIndex((item) => (item as { study_id?: string }).study_id === part);
    }
    if ('instance_id' in sample) {
      return arr.findIndex((item) => (item as { instance_id?: string }).instance_id === part);
    }
  }
  return -1;
}

export function getProjectValue(project: SimulationProject, path: string): unknown {
  const parts = path.split('.');
  let cur: unknown = project as unknown;
  for (const part of parts) {
    if (cur == null) return undefined;
    if (Array.isArray(cur)) {
      cur = resolveArraySegment(cur, part);
    } else if (typeof cur === 'object') {
      cur = (cur as Record<string, unknown>)[part];
    } else {
      return undefined;
    }
  }
  return cur;
}

export function setProjectValue(
  project: SimulationProject,
  path: string,
  value: unknown,
): SimulationProject {
  const data = structuredClone(project) as SimulationProject;
  const parts = path.split('.');
  let cur: unknown = data;
  for (let i = 0; i < parts.length - 1; i++) {
    const part = parts[i];
    if (Array.isArray(cur)) {
      const idx = resolveArrayIndex(cur, part);
      cur = idx >= 0 ? cur[idx] : undefined;
    } else if (cur && typeof cur === 'object') {
      cur = (cur as Record<string, unknown>)[part];
    } else {
      cur = undefined;
    }
    if (cur == null) break;
  }
  const last = parts[parts.length - 1];
  if (Array.isArray(cur)) {
    const idx = resolveArrayIndex(cur, last);
    if (idx >= 0) cur[idx] = value;
  } else if (cur && typeof cur === 'object') {
    (cur as Record<string, unknown>)[last] = value;
  }
  return data;
}

export function visualizationsToChartTabs(project: SimulationProject): ChartTabSchema[] {
  const viz = project.results.visualizations ?? [];
  return viz
    .filter((v) => v.implemented !== false)
    .map((v) => ({
      id: v.tab.id,
      label: v.tab.label,
      chart_type: (v.chart_type === 'line_profile' ? 'profiles' : v.chart_type) as ChartTabSchema['chart_type'],
      series_names: v.bindings.y ?? [],
      log_scale: v.bindings.log_scale ?? false,
    }));
}

type TreeWalkNode = { id: string; children?: TreeWalkNode[] };

export function findFirstSelectableTreePath(schema: {
  roots: Array<{ id: string; children?: TreeWalkNode[] }>;
}): string {
  const walk = (node: TreeWalkNode): string => {
    if (node.children?.length) {
      return walk(node.children[0]);
    }
    return node.id;
  };

  for (const root of schema.roots) {
    if (root.children?.length) {
      return walk(root.children[0]);
    }
    return root.id;
  }
  return 'model.geometry';
}
