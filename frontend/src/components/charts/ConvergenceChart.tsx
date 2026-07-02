import ReactECharts from 'echarts-for-react';
import type { ConvergenceSeries } from '../../types';
import { useLocale, tRuntime, tSeries, resolveAxisLabel } from '../../i18n';
import { useChartTheme } from '../../hooks/useChartTheme';
import { CHART_ANIMATION, seriesColor } from '../../config/chartPalette';

interface Props {
  series: ConvergenceSeries[];
  logScale?: boolean;
  height?: string;
  relativeTol?: number | null;
  replayKey?: number;
  isRunning?: boolean;
}

export function ConvergenceChart({
  series,
  logScale = true,
  height = '100%',
  relativeTol,
  replayKey = 0,
  isRunning = false,
}: Props) {
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

  const tolBand =
    relativeTol != null && relativeTol > 0
      ? {
          silent: true,
          itemStyle: { color: 'rgba(245, 158, 11, 0.08)' },
          data: [[{ yAxis: 1e-30 }, { yAxis: relativeTol }]],
        }
      : undefined;

  const markLine =
    relativeTol != null && relativeTol > 0
      ? {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#f59e0b', type: 'dashed', width: 1 },
          label: {
            formatter: tRuntime('axes.relative_tol'),
            color: ct.axisColor,
            fontSize: 10,
          },
          data: [{ yAxis: relativeTol }],
        }
      : undefined;

  const option = {
    backgroundColor: ct.backgroundColor,
    animation: !isRunning,
    animationDuration: isRunning ? 0 : CHART_ANIMATION.duration,
    animationEasing: CHART_ANIMATION.easing,
    grid: { left: 60, right: 20, top: 30, bottom: 40 },
    tooltip: { trigger: 'axis' },
    legend: {
      data: labeled.map((s) => s.label),
      textStyle: { color: ct.legendColor, fontSize: 11 },
    },
    xAxis: {
      type: 'value',
      name: resolveAxisLabel(series[0].x_label ?? t('chart.axisStep')),
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
      showSymbol: isRunning,
      symbolSize: 4,
      animationDelay: (i: number) => i * CHART_ANIMATION.delayStep,
      lineStyle: { color: seriesColor(s.name), width: 1.5 },
      itemStyle: { color: seriesColor(s.name) },
      data: s.x.map((x, i) => [x, Math.max(s.y[i], 1e-30)]),
      ...(idx === 0 && markLine ? { markLine } : {}),
      ...(idx === 0 && tolBand ? { markArea: tolBand } : {}),
    })),
  };

  return (
    <ReactECharts
      key={isRunning ? 'live' : replayKey}
      option={option}
      style={{ height, width: '100%' }}
      opts={{ renderer: 'canvas' }}
      notMerge={isRunning}
    />
  );
}
