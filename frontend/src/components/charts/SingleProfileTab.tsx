import { useMemo } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { LineProfileChart } from './LineProfileChart';
import { getCatalogItem } from '../../config/vizCatalog';
import { inferModelIdFromProject } from '../../i18n';

interface Props {
  vizId?: string;
  seriesNames?: string[];
  logScale?: boolean;
}

export function SingleProfileTab({ vizId, seriesNames, logScale }: Props) {
  const runResult = useAppStore((s) => s.runResult);
  const currentProject = useAppStore((s) => s.currentProject);
  const chartReplayKey = useAppStore((s) => s.chartReplayKey);

  const modelId = inferModelIdFromProject(currentProject);
  const catalogItem = vizId ? getCatalogItem(modelId, vizId) : undefined;
  const names = seriesNames ?? catalogItem?.seriesNames ?? [];
  const useLog = logScale ?? catalogItem?.logScale ?? false;

  const series = useMemo(() => {
    if (!runResult?.profiles.length || !names.length) return [];
    return runResult.profiles.filter((p) => names.includes(p.name));
  }, [runResult, names]);

  if (!runResult?.profiles.length) {
    return null;
  }

  return (
    <div className="h-full" key={chartReplayKey}>
      <LineProfileChart series={series} logScale={useLog} height="100%" />
    </div>
  );
}
