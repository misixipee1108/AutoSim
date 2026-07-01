import { useMemo } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { ConvergenceChart } from './ConvergenceChart';

interface Props {
  seriesNames?: string[];
}

export function ConvergenceTab({ seriesNames }: Props) {
  const runResult = useAppStore((s) => s.runResult);

  const series = useMemo(() => {
    const all = runResult?.convergence ?? [];
    if (!all.length) return [];
    if (!seriesNames?.length) return all;
    return all.filter((s) => seriesNames.includes(s.name));
  }, [runResult, seriesNames]);

  return (
    <div className="h-full">
      <ConvergenceChart
        series={series}
        relativeTol={runResult?.convergence_summary?.relative_tol ?? null}
        height="100%"
      />
    </div>
  );
}
