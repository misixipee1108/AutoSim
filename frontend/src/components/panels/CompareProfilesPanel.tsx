import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { useAppStore } from '../../store/useAppStore';
import { useLocale, resolveAxisLabel } from '../../i18n';
import { useChartTheme } from '../../hooks/useChartTheme';

const COLORS = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b'];

export function CompareProfilesPanel() {
  const { t } = useLocale();
  const ct = useChartTheme();
  const compareRunIds = useAppStore((s) => s.compareRunIds);
  const caseHistory = useAppStore((s) => s.caseHistory);
  const clearCompareRuns = useAppStore((s) => s.clearCompareRuns);

  const runs = useMemo(
    () => caseHistory.filter((c) => compareRunIds.includes(c.run_id)),
    [caseHistory, compareRunIds],
  );

  if (runs.length < 2) return null;

  const potential = runs[0].profiles.find((p) => p.name === 'potential');
  const option = {
    backgroundColor: ct.backgroundColor,
    grid: { left: 60, right: 20, top: 40, bottom: 40 },
    title: {
      text: t('history.compareOverlay'),
      textStyle: { color: ct.titleColor, fontSize: 12 },
    },
    legend: { data: runs.map((r) => r.run_id.slice(0, 8)), textStyle: { color: ct.axisColor } },
    xAxis: {
      type: 'value',
      name: resolveAxisLabel(potential?.x_label ?? 'x (cm)'),
      axisLine: { lineStyle: { color: ct.axisLineColor } },
    },
    yAxis: {
      type: 'value',
      name: resolveAxisLabel('ψ (V)'),
      axisLine: { lineStyle: { color: ct.axisLineColor } },
    },
    series: runs.map((run, i) => {
      const prof = run.profiles.find((p) => p.name === 'potential');
      return {
        name: run.run_id.slice(0, 8),
        type: 'line',
        data: prof ? prof.x.map((x, j) => [x, prof.y[j]]) : [],
        lineStyle: { color: COLORS[i % COLORS.length] },
        showSymbol: false,
      };
    }),
    tooltip: { trigger: 'axis' },
  };

  return (
    <div className="border-t border-default bg-panel px-3 py-2">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-muted">{t('history.compareOverlay')}</span>
        <button type="button" className="btn-ghost text-[10px]" onClick={clearCompareRuns}>
          {t('history.clearCompare')}
        </button>
      </div>
      <div className="h-48">
        <ReactECharts option={option} style={{ height: '100%' }} />
      </div>
    </div>
  );
}
