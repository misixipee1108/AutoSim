import ReactECharts from 'echarts-for-react';
import { useAppStore } from '../../store/useAppStore';
import { useLocale, tSeries } from '../../i18n';
import { useChartTheme } from '../../hooks/useChartTheme';

interface Props {
  seriesNames?: string[];
}

export function SweepTab({ seriesNames }: Props) {
  const { t } = useLocale();
  const ct = useChartTheme();
  const runResult = useAppStore((s) => s.runResult);
  const sweep = runResult?.sweep ?? [];

  if (sweep.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted text-sm">
        {t('chart.noSweep')}
      </div>
    );
  }

  const selected = seriesNames?.length
    ? sweep.filter((s) => seriesNames.includes(s.name))
    : sweep.slice(0, 2);
  const charts = selected.length > 0 ? selected : sweep;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 h-full min-h-0 overflow-y-auto">
      {charts.map((s) => {
        const option = {
          backgroundColor: ct.backgroundColor,
          grid: { left: 60, right: 20, top: 40, bottom: 40 },
          title: {
            text: tSeries(s.name, s.label),
            textStyle: { color: ct.titleColor, fontSize: 12 },
          },
          xAxis: {
            type: 'value',
            name: s.x_label ?? 'Vapp (V)',
            axisLine: { lineStyle: { color: ct.axisLineColor } },
            nameTextStyle: { color: ct.axisColor },
          },
          yAxis: {
            type: 'value',
            name: s.y_label ?? s.unit,
            axisLine: { lineStyle: { color: ct.axisLineColor } },
            nameTextStyle: { color: ct.axisColor },
          },
          series: [{
            type: 'line',
            data: s.x.map((x, i) => [x, s.y[i]]),
            symbol: 'circle',
            symbolSize: 6,
          }],
          tooltip: { trigger: 'axis' },
        };
        return (
          <div key={s.name} className="card p-2 min-h-[240px]">
            <ReactECharts option={option} style={{ height: '100%', minHeight: 220 }} />
          </div>
        );
      })}
    </div>
  );
}
