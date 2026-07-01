import ReactECharts from 'echarts-for-react';
import type { ConvergenceSeries } from '../../types';
import { useLocale, tSeries } from '../../i18n';
import { useChartTheme } from '../../hooks/useChartTheme';

interface Props {
  series: ConvergenceSeries[];
  logScale?: boolean;
  height?: string;
  relativeTol?: number | null;
}

export function ConvergenceChart({ series, logScale = true, height = '100%', relativeTol }: Props) {
  const { t } = useLocale();
  const ct = useChartTheme();

  if (!series.length || !series[0].x.length) {
    return (
      <div className="flex items-center justify-center h-full text-muted text-sm">
        {t('chart.noConvergence')}
      </div>
    );
  }

  const labeled = series.map((s) => ({
    ...s,
    label: tSeries(s.name, s.label),
  }));

  const isScaledView = labeled.every((s) => s.name.startsWith('scaled'));
  const yAxisName = isScaledView
    ? t('chart.scaledNorm')
    : (series[0].y_label ?? series[0].unit);

  const markLine =
    relativeTol != null && relativeTol > 0
      ? {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#f59e0b', type: 'dashed', width: 1 },
          label: {
            formatter: 'relative_tol',
            color: ct.axisColor,
            fontSize: 10,
          },
          data: [{ yAxis: relativeTol }],
        }
      : undefined;

  const option = {
    backgroundColor: ct.backgroundColor,
    grid: { left: 60, right: 20, top: 30, bottom: 40 },
    tooltip: { trigger: 'axis' },
    legend: { data: labeled.map((s) => s.label), textStyle: { color: ct.legendColor, fontSize: 11 } },
    xAxis: {
      type: 'value',
      name: series[0].x_label ?? t('chart.axisStep'),
      nameTextStyle: { color: ct.axisNameColor, fontSize: 10 },
      axisLine: { lineStyle: { color: ct.axisLineColor } },
      axisLabel: { color: ct.axisColor, fontSize: 10 },
    },
    yAxis: {
      type: logScale ? 'log' : 'value',
      name: yAxisName,
      nameTextStyle: { color: ct.axisNameColor, fontSize: 10 },
      axisLine: { lineStyle: { color: ct.axisLineColor } },
      axisLabel: { color: ct.axisColor, fontSize: 10 },
      splitLine: { lineStyle: { color: ct.splitLineColor } },
    },
    series: labeled.map((s, idx) => ({
      name: s.label,
      type: 'line',
      showSymbol: true,
      symbolSize: 4,
      data: s.x.map((x, i) => [x, Math.max(s.y[i], 1e-30)]),
      ...(idx === 0 && markLine ? { markLine } : {}),
    })),
  };

  return <ReactECharts option={option} style={{ height, width: '100%' }} opts={{ renderer: 'canvas' }} />;
}
