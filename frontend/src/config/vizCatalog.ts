import type { PhysicsModelId } from '../i18n/resolveLabels';

export type VizLayoutMode = 'separate_tabs' | 'combined';

export type VizGroup = 'profile' | 'convergence' | 'time_series';

export interface VizCatalogItem {
  id: string;
  group: VizGroup;
  /** Maps to runResult.profiles[].name or convergence[].name */
  seriesNames: string[];
  defaultEnabled: boolean;
  i18nKey: string;
  logScale?: boolean;
  /** Y-axis unit for merge validation */
  yUnit?: string;
  /** Multiple series drawn in one subplot (e.g. carriers) */
  combinedSubplot?: boolean;
}

const PN_CATALOG: VizCatalogItem[] = [
  {
    id: 'potential',
    group: 'profile',
    seriesNames: ['potential'],
    defaultEnabled: true,
    i18nKey: 'potential',
    yUnit: 'V',
  },
  {
    id: 'electric_field',
    group: 'profile',
    seriesNames: ['electric_field'],
    defaultEnabled: true,
    i18nKey: 'electric_field',
    yUnit: 'V/cm',
  },
  {
    id: 'carriers',
    group: 'profile',
    seriesNames: ['electron_density', 'hole_density'],
    defaultEnabled: false,
    i18nKey: 'carriers',
    logScale: true,
    yUnit: 'cm⁻³',
    combinedSubplot: true,
  },
  {
    id: 'charge_density',
    group: 'profile',
    seriesNames: ['charge_density'],
    defaultEnabled: false,
    i18nKey: 'charge_density',
    yUnit: 'C/cm³',
  },
  {
    id: 'convergence',
    group: 'convergence',
    seriesNames: ['scaled_residual', 'scaled_delta'],
    defaultEnabled: true,
    i18nKey: 'convergence',
  },
];

const FALLING_BLOCK_CATALOG: VizCatalogItem[] = [
  {
    id: 'position',
    group: 'time_series',
    seriesNames: ['position'],
    defaultEnabled: true,
    i18nKey: 'position',
  },
  {
    id: 'velocity',
    group: 'time_series',
    seriesNames: ['velocity'],
    defaultEnabled: true,
    i18nKey: 'velocity',
  },
  {
    id: 'energy_drift',
    group: 'convergence',
    seriesNames: ['energy_drift'],
    defaultEnabled: true,
    i18nKey: 'energy_drift',
  },
];

const CATALOGS: Record<PhysicsModelId, VizCatalogItem[]> = {
  pn_junction_1d: PN_CATALOG,
  falling_block: FALLING_BLOCK_CATALOG,
};

export function getVizCatalog(modelId: PhysicsModelId): VizCatalogItem[] {
  return CATALOGS[modelId] ?? PN_CATALOG;
}

export function getDefaultEnabledVizIds(modelId: PhysicsModelId): string[] {
  return getVizCatalog(modelId)
    .filter((item) => item.defaultEnabled)
    .map((item) => item.id);
}

export function getCatalogItem(modelId: PhysicsModelId, id: string): VizCatalogItem | undefined {
  return getVizCatalog(modelId).find((item) => item.id === id);
}

/** Flat profile series names for enabled profile-group catalog items. */
export function getEnabledProfileSeries(
  modelId: PhysicsModelId,
  enabledVizIds: string[],
): string[] {
  const names: string[] = [];
  for (const id of enabledVizIds) {
    const item = getCatalogItem(modelId, id);
    if (item?.group === 'profile') {
      for (const s of item.seriesNames) {
        if (!names.includes(s)) names.push(s);
      }
    }
  }
  return names;
}

/** Subplot panels: one entry per enabled profile catalog item (carriers = one panel). */
export function getEnabledProfilePanels(
  modelId: PhysicsModelId,
  enabledVizIds: string[],
): VizCatalogItem[] {
  return enabledVizIds
    .map((id) => getCatalogItem(modelId, id))
    .filter((item): item is VizCatalogItem => item != null && item.group === 'profile');
}

export function isVizOptionsPath(path: string | null): boolean {
  return path === 'results.visualizations' || path === 'results.output_variables';
}

const FAILED_SOLVER_STATUSES = new Set([
  'stalled',
  'not_converged',
  'failed_nan',
  'failed_unphysical',
  'max_iter_reached',
]);

export function shouldFocusConvergenceTab(solverStatus: string | null | undefined): boolean {
  if (!solverStatus) return false;
  return FAILED_SOLVER_STATUSES.has(solverStatus);
}

export function getEnabledProfileVizIds(
  modelId: PhysicsModelId,
  enabledVizIds: string[],
): string[] {
  return enabledVizIds.filter((id) => {
    const item = getCatalogItem(modelId, id);
    return item?.group === 'profile';
  });
}

export function buildDefaultChartGroups(
  modelId: PhysicsModelId,
  enabledVizIds: string[],
): string[][] {
  return getEnabledProfileVizIds(modelId, enabledVizIds).map((id) => [id]);
}

export function syncChartGroupsOnToggle(
  groups: string[][],
  vizId: string,
  enabled: boolean,
  modelId: PhysicsModelId,
): string[][] {
  const item = getCatalogItem(modelId, vizId);
  if (item?.group !== 'profile') return groups;
  if (enabled) {
    if (groups.some((g) => g.includes(vizId))) return groups;
    return [...groups, [vizId]];
  }
  return groups
    .map((g) => g.filter((x) => x !== vizId))
    .filter((g) => g.length > 0);
}

export function panelsFromChartGroups(
  modelId: PhysicsModelId,
  groups: string[][],
): VizCatalogItem[] {
  return groups
    .map((group, idx) => {
      const items = group
        .map((id) => getCatalogItem(modelId, id))
        .filter((item): item is VizCatalogItem => item != null);
      if (!items.length) return null;
      const seriesNames: string[] = [];
      for (const item of items) {
        for (const s of item.seriesNames) {
          if (!seriesNames.includes(s)) seriesNames.push(s);
        }
      }
      const logScale = items.some((i) => i.logScale);
      const panel: VizCatalogItem = {
        id: `group_${idx}_${group.join('_')}`,
        group: 'profile',
        seriesNames,
        defaultEnabled: true,
        i18nKey: items.length === 1 ? items[0].i18nKey : group.join('+'),
        logScale,
        combinedSubplot: items.length > 1 || items.some((i) => i.combinedSubplot),
      };
      return panel;
    })
    .filter((p): p is VizCatalogItem => p != null);
}

export function canMergeVizIds(modelId: PhysicsModelId, vizIds: string[]): boolean {
  if (vizIds.length < 2) return false;
  const items = vizIds
    .map((id) => getCatalogItem(modelId, id))
    .filter((item): item is VizCatalogItem => item != null);
  if (items.length !== vizIds.length) return false;
  const units = new Set(items.map((i) => `${i.logScale ? 'log' : 'linear'}:${i.yUnit ?? i.id}`));
  return units.size === 1;
}

export function findVizGroupIndex(groups: string[][], vizId: string): number {
  return groups.findIndex((g) => g.includes(vizId));
}
