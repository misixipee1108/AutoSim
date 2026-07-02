import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import type { ProfileSeries } from '../../types';
import type { VizCatalogItem } from '../../config/vizCatalog';
import { CHART_ANIMATION, seriesColor } from '../../config/chartPalette';
import { useLocale, tSeries, resolveAxisLabel } from '../../i18n';
import { useChartTheme } from '../../hooks/useChartTheme';

const PANEL_HEIGHT = 200;
const PANEL_GAP = 16;
const TITLE_OFFSET = 22;

interface Props {
  panels: VizCatalogItem[];
  profiles: ProfileSeries[];
  replayKey?: number;
  height?: string;
  junctionX?: number | null;
}

function resolveProfileData(
  profiles: ProfileSeries[],
  seriesNames: string[],
): ProfileSeries[] {
  return seriesNames
    .map((name) => profiles.find((p) => p.name === name))
    .filter((p): p is ProfileSeries => p != null && p.x.length > 0);
}

export function MultiProfileChart({
  panels,
  profiles,
  replayKey = 0,
  height = '100%',
  junctionX = 0,
}: Props) {
  const { t } = useLocale();
  const ct = useChartTheme();

  const { option, chartHeightPx } = useMemo(() => {
    const panelData = panels
      .map((panel) => ({
        panel,
        series: resolveProfileData(profiles, panel.seriesNames),
      }))
      .filter((p) => p.series.length > 0);

    if (!panelData.length) return { option: null, chartHeightPx: 0 };

    const xMin = Math.min(...panelData.flatMap((p) => p.series.flatMap((s) => s.x)));
    const xMax = Math.max(...panelData.flatMap((p) => p.series.flatMap((s) => s.x)));
    const count = panelData.length;
    const totalHeightPx =
      count * PANEL_HEIGHT + Math.max(0, count - 1) * PANEL_GAP + 48;

    const grids: Record<string, unknown>[] = [];
    const xAxes: Record<string, unknown>[] = [];
    const yAxes: Record<string, unknown>[] = [];
    const titles: Record<string, unknown>[] = [];
    const seriesList: Record<string, unknown>[] = [];

    panelData.forEach(({ panel, series }, panelIdx) => {
      const topPx = panelIdx * (PANEL_HEIGHT + PANEL_GAP) + TITLE_OFFSET;
      const panelTitle = series.map((s) => tSeries(s.name, s.label)).join(' · ');

      titles.push({
        text: panelTitle,
        left: 64,
        top: topPx - 18,
        textStyle: { color: ct.legendColor, fontSize: 11, fontWeight: 500 },
      });

      grids.push({
        left: 64,
        right: 20,
        top: topPx,
        height: PANEL_HEIGHT - 36,
      });

      const showXLabel = panelIdx === count - 1;
      xAxes.push({
        type: 'value',
        gridIndex: panelIdx,
        min: xMin,
        max: xMax,
        name: showXLabel
          ? series[0].x_label
            ? resolveAxisLabel(series[0].x_label)
            : t('chart.axisX')
          : '',
        nameTextStyle: { color: ct.axisNameColor, fontSize: 10 },
        axisLine: { lineStyle: { color: ct.axisLineColor } },
        axisLabel: {
          color: ct.axisColor,
          fontSize: 10,
          show: showXLabel,
        },
        axisPointer: { show: true },
      });

      yAxes.push({
        type: panel.logScale ? 'log' : 'value',
        gridIndex: panelIdx,
        name: series.length === 1 ? series[0].unit : '',
        nameTextStyle: { color: ct.axisNameColor, fontSize: 10 },
        axisLine: { lineStyle: { color: ct.axisLineColor } },
        axisLabel: { color: ct.axisColor, fontSize: 10 },
        splitLine: { lineStyle: { color: ct.splitLineColor } },
        logBase: 10,
      });

      series.forEach((s, sIdx) => {
        const label = tSeries(s.name, s.label);
        seriesList.push({
          name: label,
          type: 'line',
          xAxisIndex: panelIdx,
          yAxisIndex: panelIdx,
          showSymbol: false,
          animationDuration: CHART_ANIMATION.duration,
          animationEasing: CHART_ANIMATION.easing,
          animationDelay: (idx: number) => panelIdx * CHART_ANIMATION.delayStep + idx * 40,
          lineStyle: { color: seriesColor(s.name), width: 1.5 },
          itemStyle: { color: seriesColor(s.name) },
          data: s.x.map((x, i) => [
            x,
            panel.logScale ? Math.max(s.y[i], 1e-30) : s.y[i],
          ]),
          ...(sIdx === 0 &&
          junctionX != null &&
          xMin <= junctionX &&
          junctionX <= xMax
            ? {
                markLine: {
                  silent: true,
                  symbol: 'none',
                  lineStyle: { color: ct.axisLineColor, type: 'dashed', width: 1 },
                  data: [{ xAxis: junctionX }],
                },
              }
            : {}),
        });
      });
    });

    return {
      chartHeightPx: totalHeightPx,
      option: {
        backgroundColor: ct.backgroundColor,
        animation: true,
        title: titles,
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross', link: [{ xAxisIndex: 'all' }] },
          valueFormatter: (v: number) =>
            Math.abs(v) >= 1e4 || (Math.abs(v) > 0 && Math.abs(v) < 1e-3)
              ? v.toExponential(3)
              : String(Number(v.toPrecision(4))),
        },
        axisPointer: { link: [{ xAxisIndex: 'all' }] },
        grid: grids,
        xAxis: xAxes,
        yAxis: yAxes,
        series: seriesList,
      },
    };
  }, [panels, profiles, ct, t, junctionX]);

  if (!option) {
    return (
      <div className="flex items-center justify-center h-full text-muted text-sm">
        {t('chart.noProfile')}
      </div>
    );
  }

  return (
    <div className="h-full min-h-0 overflow-y-auto" style={{ height }}>
      <ReactECharts
        key={replayKey}
        option={option}
        style={{ height: chartHeightPx, width: '100%', minHeight: PANEL_HEIGHT }}
        opts={{ renderer: 'canvas' }}
        notMerge
      />
    </div>
  );
}
