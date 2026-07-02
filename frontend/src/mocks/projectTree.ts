import type { ModelTreeNode, ModelTreeSchema, SimulationProject } from '../types/project';
import {
  groupSlug,
  groupTreeLabel,
  physicsFieldLabel,
} from '../config/physicsTreeLabels';

const PN_GROUPS = ['Physics', 'Doping'] as const;
const DD_GROUPS = ['Physics', 'Doping', 'Recombination'] as const;
const FB_GROUPS = ['Body', 'Drag', 'Integration'] as const;

function groupsForInterface(interfaceId: string): readonly string[] {
  if (interfaceId === 'semiconductor_1d_dd') return DD_GROUPS;
  if (interfaceId === 'mechanics_0d_falling_body') return FB_GROUPS;
  return PN_GROUPS;
}

function categoryForInterface(interfaceId: string): string {
  if (interfaceId === 'mechanics_0d_falling_body') return 'mechanics';
  return 'semiconductor';
}

function buildPhysicsInterfaceNode(instanceId: string, interfaceId: string): ModelTreeNode {
  const category = categoryForInterface(interfaceId);
  const groups = groupsForInterface(interfaceId);
  return {
    id: `model.physics_interfaces.${instanceId}`,
    label: physicsFieldLabel(category),
    kind: 'collection',
    instance_id: instanceId,
    interface_id: interfaceId,
    physics_category: category,
    children: groups.map((group) => ({
      id: `model.physics_interfaces.${instanceId}.${groupSlug(group)}`,
      label: groupTreeLabel(group),
      kind: 'node' as const,
      instance_id: instanceId,
      interface_id: interfaceId,
      parameter_group: group,
    })),
  };
}

export function buildMockProjectTree(project: SimulationProject): ModelTreeSchema {
  const study = project.studies[0] as { study_id: string; label?: string };
  const studyId = study?.study_id ?? 'stat_equilibrium';
  const iface = (project.model.physics_interfaces as Array<{ instance_id: string; interface_id: string }>)?.[0];

  return {
    schema_version: '2.0',
    roots: [
      {
        id: 'model',
        label: 'Model',
        kind: 'section',
        children: [
          { id: 'model.geometry', label: 'Geometry', kind: 'node' },
          { id: 'model.domain', label: 'Domain', kind: 'node' },
          { id: 'model.material', label: 'Material', kind: 'node' },
          {
            id: 'model.physics_interfaces',
            label: 'Physics Interfaces',
            kind: 'collection',
            children: iface ? [buildPhysicsInterfaceNode(iface.instance_id, iface.interface_id)] : [],
          },
          { id: 'model.variables', label: 'Variables', kind: 'node' },
          { id: 'model.boundary_conditions', label: 'Boundary Conditions', kind: 'node' },
          { id: 'model.initial_conditions', label: 'Initial Conditions', kind: 'node' },
          { id: 'model.source_terms', label: 'Source Terms', kind: 'node' },
          { id: 'model.mesh', label: 'Mesh', kind: 'node' },
        ],
      },
      {
        id: 'studies',
        label: 'Simulation',
        kind: 'section',
        children: [
          {
            id: `studies.${studyId}`,
            label: study?.label ?? studyId,
            kind: 'study',
            study_id: studyId,
            children: [
              { id: `studies.${studyId}.study_params`, label: 'Study Settings', kind: 'node' },
              { id: `studies.${studyId}.solver_sequence`, label: 'Solver Sequence', kind: 'node' },
              { id: `studies.${studyId}.agent`, label: 'Agent', kind: 'node' },
            ],
          },
        ],
      },
      {
        id: 'results',
        label: 'Results',
        kind: 'section',
        children: [
          { id: 'results.output_variables', label: 'Output Variables', kind: 'node' },
          { id: 'results.visualizations', label: 'Visualizations', kind: 'node' },
          { id: 'results.postprocessing', label: 'Postprocessing', kind: 'node' },
          { id: 'results.reports', label: 'Reports', kind: 'node' },
        ],
      },
    ],
  };
}
