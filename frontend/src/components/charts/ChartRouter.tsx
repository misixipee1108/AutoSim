import { OverviewTab } from './OverviewTab';
import { ProfilesTab } from './ProfilesTab';
import { TimeSeriesTab } from './TimeSeriesTab';
import { ConvergenceTab } from './ConvergenceTab';
import { SweepTab } from './SweepTab';
import type { ChartTabSchema } from '../../types';

interface ChartRouterProps {
  tab: ChartTabSchema;
}

/** Route chart tabs by metadata chart_type instead of hard-coded tab ids. */
export function ChartRouter({ tab }: ChartRouterProps) {
  switch (tab.chart_type) {
    case 'overview':
      return <OverviewTab />;
    case 'profiles':
      return <ProfilesTab seriesNames={tab.series_names} logScale={tab.id === 'carriers'} />;
    case 'time_series':
      return <TimeSeriesTab seriesNames={tab.series_names} />;
    case 'convergence':
      return <ConvergenceTab seriesNames={tab.series_names} />;
    case 'sweep':
      return <SweepTab seriesNames={tab.series_names} />;
    case 'iv_curve':
      return <SweepTab seriesNames={tab.series_names ?? ['I_vs_Vapp']} />;
    default:
      return <OverviewTab />;
  }
}
