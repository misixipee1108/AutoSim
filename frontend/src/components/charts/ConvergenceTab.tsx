import { ConvergenceChart } from './ConvergenceChart';
import { useMemo } from 'react';
import { useAppStore } from '../../store/useAppStore';

interface Props {
  seriesNames?: string[];
}

export function ConvergenceTab({ seriesNames }: Props) {
  const runResult = useAppStore((s) => s.runResult);
  const isRunning = useAppStore((s) => s.isRunning);
  const chartReplayKey = useAppStore((s) => s.chartReplayKey);

  const series = useMemo(() => {
    const all = runResult?.convergence ?? [];
    if (!all.length) return [];
    const preferred = seriesNames?.length
      ? all.filter((s) => seriesNames.includes(s.name))
      : all.filter((s) => s.name.startsWith('scaled'));
    return preferred.length ? preferred : all;
  }, [runResult, seriesNames]);

  return (
    <div className="h-full">
      <ConvergenceChart
        series={series}
        relativeTol={runResult?.convergence_summary?.relative_tol ?? null}
        height="100%"
        replayKey={chartReplayKey}
        isRunning={isRunning}
      />
    </div>
  );
}
