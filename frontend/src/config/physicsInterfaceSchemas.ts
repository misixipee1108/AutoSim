import type { ParameterSchema, SimulationProject } from '../types';

/** Parameter templates keyed by physics interface_id (mirrors backend plugin manifests). */
export const PHYSICS_INTERFACE_PARAM_TEMPLATES: Record<string, ParameterSchema[]> = {
  semiconductor_1d_poisson: [
    {
      name: 'settings.model_type',
      label: 'Physics Model',
      type: 'select',
      default: 'poisson',
      group: 'Physics',
      options: [
        { value: 'poisson', label: 'Nonlinear Poisson' },
        { value: 'depletion', label: 'Depletion Approximation' },
        { value: 'drift_diffusion', label: 'Drift-Diffusion' },
        { value: 'transient_dd', label: 'Transient DD' },
      ],
    },
    {
      name: 'settings.doping.type',
      label: 'Doping Profile',
      type: 'select',
      default: 'abrupt',
      group: 'Doping',
      options: [
        { value: 'abrupt', label: 'Abrupt' },
        { value: 'linear_graded', label: 'Linear Graded' },
        { value: 'gaussian', label: 'Gaussian' },
        { value: 'erfc', label: 'Erfc' },
        { value: 'piecewise', label: 'Piecewise' },
      ],
    },
    {
      name: 'settings.doping.Na',
      label: 'Acceptor Na',
      type: 'number',
      unit: 'cm⁻³',
      default: 1e18,
      min: 1e14,
      max: 1e20,
      group: 'Doping',
    },
    {
      name: 'settings.doping.Nd',
      label: 'Donor Nd',
      type: 'number',
      unit: 'cm⁻³',
      default: 1e16,
      min: 1e14,
      max: 1e20,
      group: 'Doping',
    },
    {
      name: 'settings.carrier_model',
      label: 'Carrier Model',
      type: 'select',
      default: 'boltzmann',
      group: 'Physics',
      options: [{ value: 'boltzmann', label: 'Boltzmann' }],
    },
  ],
  semiconductor_1d_dd: [
    {
      name: 'settings.model_type',
      label: 'Physics Model',
      type: 'select',
      default: 'drift_diffusion',
      group: 'Physics',
      options: [
        { value: 'drift_diffusion', label: 'Drift-Diffusion' },
        { value: 'transient_dd', label: 'Transient DD' },
      ],
    },
    {
      name: 'settings.doping.type',
      label: 'Doping Profile',
      type: 'select',
      default: 'abrupt',
      group: 'Doping',
      options: [
        { value: 'abrupt', label: 'Abrupt' },
        { value: 'linear_graded', label: 'Linear Graded' },
        { value: 'gaussian', label: 'Gaussian' },
        { value: 'erfc', label: 'Erfc' },
        { value: 'piecewise', label: 'Piecewise' },
      ],
    },
    {
      name: 'settings.doping.Na',
      label: 'Acceptor Na',
      type: 'number',
      unit: 'cm⁻³',
      default: 1e18,
      min: 1e14,
      max: 1e20,
      group: 'Doping',
    },
    {
      name: 'settings.doping.Nd',
      label: 'Donor Nd',
      type: 'number',
      unit: 'cm⁻³',
      default: 1e16,
      min: 1e14,
      max: 1e20,
      group: 'Doping',
    },
    {
      name: 'settings.recombination.enabled',
      label: 'Recombination',
      type: 'boolean',
      default: false,
      group: 'Recombination',
    },
    {
      name: 'settings.recombination.srh',
      label: 'SRH',
      type: 'boolean',
      default: true,
      group: 'Recombination',
    },
    {
      name: 'settings.recombination.tau_n',
      label: 'τn',
      type: 'number',
      unit: 's',
      default: 1e-6,
      group: 'Recombination',
    },
    {
      name: 'settings.recombination.tau_p',
      label: 'τp',
      type: 'number',
      unit: 's',
      default: 1e-6,
      group: 'Recombination',
    },
  ],
};

export function resolvePhysicsInterfaceParameters(
  project: SimulationProject,
  instanceId: string,
  getValue: (project: SimulationProject, path: string) => unknown,
  groupName?: string,
): ParameterSchema[] {
  const ifaces = (project.model.physics_interfaces ?? []) as Array<{
    instance_id: string;
    interface_id: string;
  }>;
  const instance = ifaces.find((i) => i.instance_id === instanceId);
  if (!instance) return [];

  const templates = PHYSICS_INTERFACE_PARAM_TEMPLATES[instance.interface_id];
  if (!templates) return [];

  const prefix = `model.physics_interfaces.${instanceId}.settings`;
  return templates
    .filter((p) => !groupName || p.group === groupName)
    .map((p) => {
    let name = p.name;
    if (name.startsWith('settings.')) {
      name = `model.physics_interfaces.${instanceId}.${name}`;
    } else if (!name.startsWith('model.')) {
      name = `${prefix}.${name}`;
    }
    const current = getValue(project, name);
    return {
      ...p,
      name,
      default: current !== undefined ? current : p.default,
    };
  });
}