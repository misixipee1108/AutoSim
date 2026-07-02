import type { ChartTabSchema, SimulationProject } from '../types';
import type { PhysicsModelId } from '../i18n/resolveLabels';
import { resolveChartTabLabel } from '../i18n/resolveLabels';
import { tModel } from '../i18n/translations';
import {
  getEnabledProfileSeries,
  getEnabledProfileVizIds,
  getCatalogItem,
  getVizCatalog,
  type VizLayoutMode,
} from '../config/vizCatalog';
import { visualizationsToChartTabs } from './projectParameters';

const BUILTIN_TAB_IDS = new Set(['overview', 'profiles', 'convergence']);

function profileTabLabel(modelId: PhysicsModelId, vizId: string): string {
  const item = getCatalogItem(modelId, vizId);
  if (!item) return vizId;
  return tModel(modelId, `vizOptions.${item.i18nKey}.label`, item.i18nKey);
}

export function buildChartTabs(
  project: SimulationProject,
  enabledVizIds: string[],
  modelId: PhysicsModelId,
  vizLayoutMode: VizLayoutMode = 'separate_tabs',
  vizChartGroups: string[][] = [],
): ChartTabSchema[] {
  const profileVizIds = getEnabledProfileVizIds(modelId, enabledVizIds);
  const hasProfiles = profileVizIds.length > 0;
  const hasConvergence = enabledVizIds.includes('convergence');
  const groups =
    vizChartGroups.length > 0
      ? vizChartGroups
      : profileVizIds.map((id) => [id]);

  const tabs: ChartTabSchema[] = [
    {
      id: 'overview',
      label: resolveChartTabLabel('overview', 'Overview', modelId),
      chart_type: 'overview',
    },
  ];

  if (hasProfiles) {
    if (vizLayoutMode === 'separate_tabs') {
      for (const vizId of profileVizIds) {
        const item = getCatalogItem(modelId, vizId);
        if (!item) continue;
        tabs.push({
          id: `profile_${vizId}`,
          label: profileTabLabel(modelId, vizId),
          chart_type: 'profile_single',
          viz_id: vizId,
          series_names: item.seriesNames,
          log_scale: item.logScale,
        });
      }
    } else {
      tabs.push({
        id: 'profiles',
        label: resolveChartTabLabel('profiles', 'Profiles', modelId),
        chart_type: 'profiles_combined',
        series_names: getEnabledProfileSeries(modelId, enabledVizIds),
        viz_groups: groups,
      });
    }
  }

  if (hasConvergence) {
    tabs.push({
      id: 'convergence',
      label: resolveChartTabLabel('convergence', 'Convergence', modelId),
      chart_type: 'convergence',
      series_names: ['scaled_residual', 'scaled_delta'],
    });
  }

  for (const pt of visualizationsToChartTabs(project)) {
    if (BUILTIN_TAB_IDS.has(pt.id)) continue;
    if (tabs.some((t) => t.id === pt.id)) continue;
    tabs.push({
      ...pt,
      label: resolveChartTabLabel(pt.id, pt.label, modelId),
    });
  }

  if (modelId === 'pn_junction_1d' && tabs.length === 1) {
    const catalog = getVizCatalog(modelId);
    const defaults = catalog.filter((c) => c.defaultEnabled);
    const defaultProfileIds = defaults
      .filter((c) => c.group === 'profile')
      .map((c) => c.id);
    if (defaultProfileIds.length) {
      if (vizLayoutMode === 'separate_tabs') {
        for (const vizId of defaultProfileIds) {
          const item = getCatalogItem(modelId, vizId);
          if (!item) continue;
          tabs.push({
            id: `profile_${vizId}`,
            label: profileTabLabel(modelId, vizId),
            chart_type: 'profile_single',
            viz_id: vizId,
            series_names: item.seriesNames,
            log_scale: item.logScale,
          });
        }
      } else {
        tabs.push({
          id: 'profiles',
          label: resolveChartTabLabel('profiles', 'Profiles', modelId),
          chart_type: 'profiles_combined',
          series_names: getEnabledProfileSeries(modelId, defaultProfileIds),
          viz_groups: defaultProfileIds.map((id) => [id]),
        });
      }
    }
    if (defaults.some((c) => c.id === 'convergence')) {
      tabs.push({
        id: 'convergence',
        label: resolveChartTabLabel('convergence', 'Convergence', modelId),
        chart_type: 'convergence',
        series_names: ['scaled_residual', 'scaled_delta'],
      });
    }
  }

  return tabs;
}

export function resolveActiveChartTab(
  tabs: ChartTabSchema[],
  currentTabId: string,
): string {
  const ids = new Set(tabs.map((t) => t.id));
  return ids.has(currentTabId) ? currentTabId : (tabs[0]?.id ?? 'overview');
}

export function firstProfileTabId(
  enabledVizIds: string[],
  modelId: PhysicsModelId,
  vizLayoutMode: VizLayoutMode,
): string | null {
  const profileVizIds = getEnabledProfileVizIds(modelId, enabledVizIds);
  if (!profileVizIds.length) return null;
  return vizLayoutMode === 'separate_tabs'
    ? `profile_${profileVizIds[0]}`
    : 'profiles';
}
