import { useMemo } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { MultiProfileChart } from './MultiProfileChart';
import {
  buildDefaultChartGroups,
  panelsFromChartGroups,
} from '../../config/vizCatalog';
import { inferModelIdFromProject } from '../../i18n';

interface Props {
  seriesNames?: string[];
  vizGroups?: string[][];
}

export function ProfilesTab({ seriesNames, vizGroups }: Props) {
  const runResult = useAppStore((s) => s.runResult);
  const currentProject = useAppStore((s) => s.currentProject);
  const enabledVizIds = useAppStore((s) => s.enabledVizIds);
  const storeGroups = useAppStore((s) => s.vizChartGroups);
  const chartReplayKey = useAppStore((s) => s.chartReplayKey);

  const modelId = inferModelIdFromProject(currentProject);

  const panels = useMemo(() => {
    const groups =
      vizGroups ??
      (storeGroups.length > 0
        ? storeGroups
        : buildDefaultChartGroups(modelId, enabledVizIds));
    const fromGroups = panelsFromChartGroups(modelId, groups);
    if (fromGroups.length) return fromGroups;
    if (!seriesNames?.length) return [];
    return seriesNames.map((name) => ({
      id: name,
      group: 'profile' as const,
      seriesNames: [name],
      defaultEnabled: true,
      i18nKey: name,
      logScale: name.includes('density'),
    }));
  }, [modelId, vizGroups, storeGroups, enabledVizIds, seriesNames]);

  const junctionX =
    (currentProject?.model?.geometry as { junction_position?: number } | undefined)
      ?.junction_position ?? 0;

  if (!runResult?.profiles.length) {
    return null;
  }

  return (
    <div className="h-full min-h-0">
      <MultiProfileChart
        panels={panels}
        profiles={runResult.profiles}
        replayKey={chartReplayKey}
        height="100%"
        junctionX={junctionX}
      />
    </div>
  );
}
