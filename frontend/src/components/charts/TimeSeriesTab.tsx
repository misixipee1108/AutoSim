import { useMemo } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { TimeSeriesChart } from './TimeSeriesChart';

interface Props {
  seriesNames?: string[];
}

export function TimeSeriesTab({ seriesNames }: Props) {
  const runResult = useAppStore((s) => s.runResult);

  const series = useMemo(() => {
    if (!runResult?.time_series.length) return [];
    if (!seriesNames?.length) {
      return runResult.time_series;
    }
    return runResult.time_series.filter((s) => seriesNames.includes(s.name));
  }, [runResult, seriesNames]);

  return (
    <div className="h-full">
      <TimeSeriesChart series={series} height="100%" />
    </div>
  );
}
