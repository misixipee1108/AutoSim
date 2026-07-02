import ReactECharts from 'echarts-for-react';

import { useMemo } from 'react';

import { useAppStore } from '../../store/useAppStore';

import { useLocale, tRuntime, resolveAxisLabel, tMetric } from '../../i18n';

import { useChartTheme } from '../../hooks/useChartTheme';



export function OptimizationTab() {

  const { t } = useLocale();

  const ct = useChartTheme();

  const runResult = useAppStore((s) => s.runResult);



  const { scatter, table } = useMemo(() => {

    const trials = runResult?.trials ?? [];

    if (trials.length === 0) {

      return { scatter: null, table: [] as Array<{ idx: number; w: number; emax: number; status: string }> };

    }

    const rows = trials.map((tr) => {

      const wRaw = tr.scalars.W;

      const emaxRaw = tr.scalars.Emax;

      const wVal = wRaw && typeof wRaw === 'object' && 'value' in wRaw ? wRaw.value : wRaw;

      const emaxVal = emaxRaw && typeof emaxRaw === 'object' && 'value' in emaxRaw ? emaxRaw.value : emaxRaw;

      return {

        idx: tr.trial_index,

        w: typeof wVal === 'number' ? wVal : 0,

        emax: typeof emaxVal === 'number' ? emaxVal : 0,

        status: tr.status,

      };

    });

    const points = rows.map((r) => [r.emax, r.w, r.idx]);

    return { scatter: points, table: rows };

  }, [runResult]);



  if (!scatter || scatter.length === 0) {

    return (

      <div className="flex items-center justify-center h-full text-muted text-sm">

        {t('chart.noOptimization')}

      </div>

    );

  }



  const option = {

    backgroundColor: ct.backgroundColor,

    grid: { left: 60, right: 20, top: 40, bottom: 40 },

    title: {

      text: t('chart.optimizationScatter'),

      textStyle: { color: ct.titleColor, fontSize: 12 },

    },

    xAxis: {

      type: 'value',

      name: resolveAxisLabel('Emax (V/cm)'),

      axisLine: { lineStyle: { color: ct.axisLineColor } },

      nameTextStyle: { color: ct.axisColor },

    },

    yAxis: {

      type: 'value',

      name: resolveAxisLabel('W (cm)'),

      axisLine: { lineStyle: { color: ct.axisLineColor } },

      nameTextStyle: { color: ct.axisColor },

    },

    series: [{

      type: 'scatter',

      data: scatter,

      symbolSize: 10,

    }],

    tooltip: {

      trigger: 'item',

      formatter: (p: { data: number[] }) =>

        `${t('chart.trialIndex')} ${p.data[2]}<br/>${tMetric('Emax')}: ${p.data[0].toExponential(2)}<br/>${tMetric('W')}: ${p.data[1].toExponential(2)}`,

    },

  };



  return (

    <div className="h-full flex flex-col gap-2 min-h-0 overflow-y-auto">

      <div className="card p-2 flex-1 min-h-[240px]">

        <ReactECharts option={option} style={{ height: '100%', minHeight: 220 }} />

      </div>

      <div className="card p-2 max-h-40 overflow-y-auto">

        <table className="w-full text-xs">

          <thead>

            <tr className="text-faint">

              <th className="text-left py-0.5">{t('chart.trialIndex')}</th>

              <th className="text-left">{tMetric('W')}</th>

              <th className="text-left">{tMetric('Emax')}</th>

              <th className="text-left">{t('chart.trialStatus')}</th>

            </tr>

          </thead>

          <tbody>

            {table.map((row) => (

              <tr key={row.idx} className="border-t border-subtle">

                <td className="py-0.5 font-mono">{row.idx}</td>

                <td>{typeof row.w === 'number' ? row.w.toExponential(2) : '—'}</td>

                <td>{typeof row.emax === 'number' ? row.emax.toExponential(2) : '—'}</td>

                <td>{tRuntime(`status.${row.status}`, row.status)}</td>

              </tr>

            ))}

          </tbody>

        </table>

      </div>

    </div>

  );

}


