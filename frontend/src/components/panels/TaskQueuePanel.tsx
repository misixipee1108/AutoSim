import { useAppStore } from '../../store/useAppStore';
import { useLocale, tRuntime } from '../../i18n';

export function TaskQueuePanel() {
  const { t } = useLocale();
  const isRunning = useAppStore((s) => s.isRunning);
  const runStatus = useAppStore((s) => s.runStatus);

  const statusLabel = isRunning
    ? t('task.running')
    : runStatus
      ? tRuntime(`status.${runStatus}`, runStatus)
      : t('task.idle');

  return (
    <div className="px-3 py-2 border-t border-default text-xs text-muted">
      {t('task.queue')}: {statusLabel}
    </div>
  );
}
