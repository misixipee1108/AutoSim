import { useMemo } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { LineProfileChart } from './LineProfileChart';

interface Props {
  seriesNames?: string[];
  logScale?: boolean;
}

export function ProfilesTab({ seriesNames, logScale: logScaleProp }: Props) {
  const runResult = useAppStore((s) => s.runResult);

  const series = useMemo(() => {
    if (!runResult?.profiles.length) return [];
    if (!seriesNames?.length) return runResult.profiles;
    const carrierLike = ['electron_density', 'hole_density', 'charge_density', 'carriers'];
    if (seriesNames.some((n) => carrierLike.includes(n))) {
      return runResult.profiles.filter((p) =>
        ['electron_density', 'hole_density', 'charge_density'].includes(p.name),
      );
    }
    return runResult.profiles.filter((p) => seriesNames.includes(p.name));
  }, [runResult, seriesNames]);

  const logScale = logScaleProp ?? series.some((s) => s.name.includes('density'));

  return (
    <div className="h-full">
      <LineProfileChart series={series} logScale={logScale} height="100%" />
    </div>
  );
}
