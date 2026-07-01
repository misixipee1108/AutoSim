import type { ReactNode } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { useLocale, tModel, tRuntime } from '../../i18n';

const RUN_STATUS_CLASS: Record<string, string> = {
  pending: 'status-pending',
  running: 'status-running',
  completed: 'status-completed',
  completed_with_warning: 'status-warning',
  failed: 'status-failed',
  early_stopped: 'status-early_stopped',
};

const SOLVER_STATUS_CLASS: Record<string, string> = {
  converged: 'status-completed',
  analytic_complete: 'status-completed',
  max_iter_reached: 'status-warning',
  not_converged: 'status-failed',
  failed_nan: 'status-failed',
  failed_unphysical: 'status-failed',
  stalled: 'status-failed',
  early_stopped: 'status-early_stopped',
};

const VALIDATION_STATUS_CLASS: Record<string, string> = {
  passed: 'status-completed',
  failed: 'status-failed',
  unavailable: 'status-pending',
  numerical_only: 'status-pending',
};

function formatSci(value: number): string {
  if (value === 0) return '0';
  if (Math.abs(value) >= 1e-3 && Math.abs(value) < 1e4) return value.toExponential(3);
  return value.toExponential(3);
}

export function SolverStatusPanel() {
  const { t } = useLocale();
  const runStatus = useAppStore((s) => s.runStatus);
  const runId = useAppStore((s) => s.runId);
  const isRunning = useAppStore((s) => s.isRunning);
  const runResult = useAppStore((s) => s.runResult);
  const descriptor = useAppStore((s) => s.currentDescriptor);

  const modelLabel = descriptor
    ? tModel(descriptor.model_id, 'name', descriptor.model_name)
    : t('solver.empty');

  const runStatusKey = runResult?.run_status ?? runStatus ?? null;
  const solverStatusKey = runResult?.solver_status ?? null;
  const validationStatusKey = runResult?.validation_status ?? null;
  const conv = runResult?.convergence_summary;

  return (
    <div className="border-b border-default">
      <div className="panel-header">{t('panel.solverStatus')}</div>
      <div className="p-3 space-y-2 text-xs">
        <Row label={t('solver.model')} value={modelLabel} />
        <Row label={t('solver.runId')} value={runId ?? t('solver.empty')} mono />
        <StatusRow
          label={t('solver.runStatus')}
          statusKey={runStatusKey}
          ns="runStatus"
          classMap={RUN_STATUS_CLASS}
        />
        <StatusRow
          label={t('solver.solverStatus')}
          statusKey={solverStatusKey}
          ns="solverStatus"
          classMap={SOLVER_STATUS_CLASS}
        />
        <StatusRow
          label={t('solver.validationStatus')}
          statusKey={validationStatusKey}
          ns="validationStatus"
          classMap={VALIDATION_STATUS_CLASS}
          hint={runResult?.validation_reason ?? undefined}
        />
        <Row
          label={t('solver.running')}
          value={isRunning ? t('solver.yes') : t('solver.no')}
        />
        {runResult && (
          <>
            <Row label={t('solver.trial')} value={String(runResult.trial_index)} />
            {runResult.convergence[0] && (
              <Row
                label={t('solver.steps')}
                value={String(runResult.convergence[0].x.length)}
              />
            )}
          </>
        )}
        {conv && (
          <div className="pt-2 mt-2 border-t border-subtle space-y-1.5">
            <div className="text-[10px] font-semibold text-muted uppercase">
              {t('solver.convergenceSection')}
            </div>
            <Row
              label={t('convergence.criterion')}
              value={tRuntime(`convergenceCriterion.${conv.criterion}`, conv.criterion)}
            />
            <Row label={t('convergence.relativeTol')} value={formatSci(conv.relative_tol)} mono />
            <Row label={t('convergence.residualScale')} value={formatSci(conv.residual_scale)} mono />
            <Row label={t('convergence.solutionScale')} value={formatSci(conv.solution_scale)} mono />
            <Row
              label={t('convergence.finalScaledResidual')}
              value={formatSci(conv.final_scaled_residual_norm)}
              mono
            />
            <Row
              label={t('convergence.finalScaledDelta')}
              value={formatSci(conv.final_scaled_delta_norm)}
              mono
            />
            <Row
              label={t('convergence.criterionMet')}
              value={tRuntime(`convergenceMet.${conv.criterion_met}`, conv.criterion_met)}
            />
            {conv.solver_warnings && conv.solver_warnings.length > 0 && (
              <Row
                label={t('convergence.warnings')}
                value={conv.solver_warnings.join(', ')}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function StatusRow({
  label,
  statusKey,
  ns,
  classMap,
  hint,
}: {
  label: string;
  statusKey: string | null;
  ns: 'runStatus' | 'solverStatus' | 'validationStatus';
  classMap: Record<string, string>;
  hint?: string;
}) {
  const { t } = useLocale();
  if (!statusKey) {
    return <Row label={label} value={t('solver.empty')} />;
  }
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex justify-between items-center gap-2">
        <span className="text-muted">{label}</span>
        <span className={`status-badge ${classMap[statusKey] ?? ''}`}>
          {tRuntime(`${ns}.${statusKey}`, statusKey)}
        </span>
      </div>
      {hint && <span className="text-[10px] text-faint text-right">{hint}</span>}
    </div>
  );
}

function Row({
  label,
  value,
  mono,
  children,
}: {
  label: string;
  value?: string;
  mono?: boolean;
  children?: ReactNode;
}) {
  return (
    <div className="flex justify-between items-center gap-2">
      <span className="text-muted">{label}</span>
      {children ?? (
        <span className={`text-primary truncate max-w-[140px] ${mono ? 'font-mono text-[10px]' : ''}`}>
          {value}
        </span>
      )}
    </div>
  );
}
