import ReactECharts from 'echarts-for-react';
import type { TimeSeries } from '../../types';
import { useLocale, tSeries } from '../../i18n';
import { useChartTheme } from '../../hooks/useChartTheme';

interface Props {
  series: TimeSeries[];
  height?: string;
}

export function TimeSeriesChart({ series, height = '100%' }: Props) {
  const { t } = useLocale();
  const ct = useChartTheme();

  if (!series.length || !series[0].t.length) {
    return (
      <div className="flex items-center justify-center h-full text-muted text-sm">
        {t('chart.noTimeSeries')}
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
      name: t('chart.axisTime'),
      nameTextStyle: { color: ct.axisNameColor, fontSize: 10 },
      axisLine: { lineStyle: { color: ct.axisLineColor } },
      axisLabel: { color: ct.axisColor, fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: ct.axisLineColor } },
      axisLabel: { color: ct.axisColor, fontSize: 10 },
      splitLine: { lineStyle: { color: ct.splitLineColor } },
    },
    series: labeled.map((s) => ({
      name: `${s.label} (${s.unit})`,
      type: 'line',
      showSymbol: false,
      data: s.t.map((tVal, i) => [tVal, s.y[i]]),
    })),
  };

  return <ReactECharts option={option} style={{ height, width: '100%' }} opts={{ renderer: 'canvas' }} />;
}
