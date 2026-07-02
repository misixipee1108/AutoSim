import ReactECharts from 'echarts-for-react';
import type { ProfileSeries } from '../../types';
import { useLocale, tSeries, resolveAxisLabel } from '../../i18n';
import { useChartTheme } from '../../hooks/useChartTheme';

interface Props {
  series: ProfileSeries[];
  logScale?: boolean;
  height?: string;
}

export function LineProfileChart({ series, logScale = false, height = '100%' }: Props) {
  const { t } = useLocale();
  const ct = useChartTheme();

  if (!series.length || !series[0].x.length) {
    return (
      <div className="flex items-center justify-center h-full text-muted text-sm">
        {t('chart.noProfile')}
      </div>
    );
  }

  const labeled = series.map((s) => ({
    ...s,
    label: tSeries(s.name, s.label),
  }));

  const option = {
    backgroundColor: ct.backgroundColor,
    grid: { left: 60, right: 20, top: 30, bottom: 40 },
    tooltip: { trigger: 'axis' },
    legend: { data: labeled.map((s) => s.label), textStyle: { color: ct.legendColor, fontSize: 11 } },
    xAxis: {
      type: 'value',
      name: series[0].x_label ? resolveAxisLabel(series[0].x_label) : t('chart.axisX'),
      nameTextStyle: { color: ct.axisNameColor, fontSize: 10 },
      axisLine: { lineStyle: { color: ct.axisLineColor } },
      axisLabel: { color: ct.axisColor, fontSize: 10 },
    },
    yAxis: {
      type: logScale ? 'log' : 'value',
      name: series[0].unit,
      nameTextStyle: { color: ct.axisNameColor, fontSize: 10 },
      axisLine: { lineStyle: { color: ct.axisLineColor } },
      axisLabel: { color: ct.axisColor, fontSize: 10 },
      splitLine: { lineStyle: { color: ct.splitLineColor } },
    },
    series: labeled.map((s) => ({
      name: s.label,
      type: 'line',
      showSymbol: false,
      data: s.x.map((x, i) => [x, s.y[i]]),
    })),
  };

  return <ReactECharts option={option} style={{ height, width: '100%' }} opts={{ renderer: 'canvas' }} />;
}
