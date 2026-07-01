import { useAppStore } from '../../store/useAppStore';
import {
  useLocale,
  tModel,
  tCategory,
  tDimension,
  tRuntime,
  tMetric,
} from '../../i18n';

export function OverviewTab() {
  const { t } = useLocale();
  const descriptor = useAppStore((s) => s.currentDescriptor);
  const runResult = useAppStore((s) => s.runResult);
  const config = useAppStore((s) => s.config);
  const runStatus = useAppStore((s) => s.runStatus);

  if (!descriptor) return null;

  const modelName = tModel(descriptor.model_id, 'name', descriptor.model_name);
  const categoryLine = `${tCategory(descriptor.model_id, descriptor.category)} · ${tDimension(descriptor.dimension)}`;
  const runStatusKey = runResult?.run_status ?? runStatus;
  const solverStatusKey = runResult?.solver_status;
  const validationStatusKey = runResult?.validation_status;
  const runStatusLabel = runStatusKey
    ? tRuntime(`runStatus.${runStatusKey}`, runStatusKey)
    : t('overview.idle');
  const solverStatusLabel = solverStatusKey
    ? tRuntime(`solverStatus.${solverStatusKey}`, solverStatusKey)
    : t('overview.idle');
  const validationStatusLabel = validationStatusKey
    ? tRuntime(`validationStatus.${validationStatusKey}`, validationStatusKey)
    : t('overview.idle');

  return (
    <div className="h-full overflow-y-auto space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <InfoCard title={t('overview.model')} value={modelName} />
        <InfoCard title={t('overview.category')} value={categoryLine} />
        <InfoCard title={t('overview.runStatus')} value={runStatusLabel} />
        <InfoCard title={t('overview.solverStatus')} value={solverStatusLabel} />
        <InfoCard title={t('overview.validationStatus')} value={validationStatusLabel} />
        <InfoCard
          title={t('overview.description')}
          value={tModel(descriptor.model_id, 'description', descriptor.description)}
          wide
        />
      </div>

      {runResult && Object.keys(runResult.scalars).length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-muted mb-2 uppercase">{t('overview.keyMetrics')}</h3>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(runResult.scalars).map(([key, m]) => (
              <div key={key} className="card">
                <div className="text-[10px] text-faint">{tMetric(key, m.label || key)}</div>
                <div className="text-sm font-mono text-primary">
                  {formatValue(m.value)} {m.unit}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {runResult?.trials && runResult.trials.length > 1 && (
        <div>
          <h3 className="text-xs font-semibold text-muted mb-2 uppercase">{t('overview.trialsSummary')}</h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-faint border-b border-default">
                <th className="text-left py-1">{t('table.trial')}</th>
                <th className="text-left py-1">{t('table.status')}</th>
                <th className="text-right py-1">{tMetric('Vapp', 'Vapp')}</th>
                <th className="text-right py-1">{tMetric('W', 'W')}</th>
                <th className="text-right py-1">{tMetric('Emax', 'Emax')}</th>
              </tr>
            </thead>
            <tbody>
              {runResult.trials.map((trial) => (
                <tr key={trial.trial_index} className="border-b border-subtle">
                  <td className="py-1">{trial.trial_index}</td>
                  <td className="py-1">{tRuntime(`status.${trial.status}`, trial.status)}</td>
                  <td className="py-1 text-right font-mono">{formatValue(trial.scalars.Vapp?.value ?? 0)}</td>
                  <td className="py-1 text-right font-mono">{formatValue(trial.scalars.W?.value ?? 0)}</td>
                  <td className="py-1 text-right font-mono">{formatValue(trial.scalars.Emax?.value ?? 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {runResult?.convergence_summary && (
        <div>
          <h3 className="text-xs font-semibold text-muted mb-2 uppercase">{t('overview.convergence')}</h3>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="card px-2 py-1">
              <div className="text-[10px] text-faint">{t('convergence.criterion')}</div>
              <div>{tRuntime(`convergenceCriterion.${runResult.convergence_summary.criterion}`, runResult.convergence_summary.criterion)}</div>
            </div>
            <div className="card px-2 py-1">
              <div className="text-[10px] text-faint">{t('convergence.relativeTol')}</div>
              <div className="font-mono">{formatValue(runResult.convergence_summary.relative_tol)}</div>
            </div>
            <div className="card px-2 py-1">
              <div className="text-[10px] text-faint">{t('convergence.finalScaledResidual')}</div>
              <div className="font-mono">{formatValue(runResult.convergence_summary.final_scaled_residual_norm)}</div>
            </div>
            <div className="card px-2 py-1">
              <div className="text-[10px] text-faint">{t('convergence.finalScaledDelta')}</div>
              <div className="font-mono">{formatValue(runResult.convergence_summary.final_scaled_delta_norm)}</div>
            </div>
            <div className="card px-2 py-1">
              <div className="text-[10px] text-faint">{t('convergence.residualScale')}</div>
              <div className="font-mono">{formatValue(runResult.convergence_summary.residual_scale)}</div>
            </div>
            <div className="card px-2 py-1">
              <div className="text-[10px] text-faint">{t('convergence.solutionScale')}</div>
              <div className="font-mono">{formatValue(runResult.convergence_summary.solution_scale)}</div>
            </div>
          </div>
        </div>
      )}

      {runResult?.validation_status && (
        <div className="text-xs text-faint">
          {runResult.validation_reason && (
            <p>{runResult.validation_reason}</p>
          )}
        </div>
      )}

      {runResult?.validation && (
        <div>
          <h3 className="text-xs font-semibold text-muted mb-2 uppercase">{t('overview.validation')}</h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-faint border-b border-default">
                <th className="text-left py-1">{t('table.metric')}</th>
                <th className="text-right py-1">{t('table.numeric')}</th>
                <th className="text-right py-1">{t('table.analytic')}</th>
                <th className="text-right py-1">{t('table.relError')}</th>
                <th className="text-center py-1">{t('table.pass')}</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(runResult.validation).map(([key, v]) => (
                <tr key={key} className="border-b border-subtle">
                  <td className="py-1 text-primary">{tMetric(key, key)}</td>
                  <td className="py-1 text-right font-mono">{formatValue(v.numeric)}</td>
                  <td className="py-1 text-right font-mono">{formatValue(v.analytic)}</td>
                  <td className="py-1 text-right font-mono">{(v.rel_error * 100).toFixed(1)}%</td>
                  <td className="py-1 text-center">{v.passed ? '✓' : '✗'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!runResult && (
        <div className="text-sm text-faint mt-4">
          <p>
            {t('overview.configureHint')}{' '}
            <strong className="text-accent">{t('shell.run')}</strong>
            {t('overview.configureHintEnd')}
          </p>
          <p className="mt-2 text-xs">{t('overview.configPreview')}</p>
          <pre className="mt-1 p-2 bg-panel-solid rounded text-[10px] overflow-auto max-h-40 border border-subtle">
            {JSON.stringify(config, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function InfoCard({ title, value, wide }: { title: string; value: string; wide?: boolean }) {
  return (
    <div className={`card px-3 py-2 ${wide ? 'col-span-2' : ''}`}>
      <div className="text-[10px] text-faint uppercase">{title}</div>
      <div className="text-sm text-primary">{value}</div>
    </div>
  );
}

function formatValue(v: number): string {
  if (Math.abs(v) >= 1e6 || (Math.abs(v) < 1e-3 && v !== 0)) return v.toExponential(3);
  return v.toPrecision(4);
}
