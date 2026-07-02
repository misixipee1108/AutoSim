import { useAppStore } from '../../store/useAppStore';

import { useLocale, tRuntime } from '../../i18n';



export function TaskQueuePanel() {

  const { t } = useLocale();

  const isRunning = useAppStore((s) => s.isRunning);

  const runStatus = useAppStore((s) => s.runStatus);

  const benchmarkRunning = useAppStore((s) => s.benchmarkRunning);

  const workspace = useAppStore((s) => s.workspace);



  let statusLabel = t('task.idle');

  if (benchmarkRunning) {

    statusLabel = t('task.benchmarkRunning');

  } else if (isRunning) {

    statusLabel = t('task.running');

  } else if (runStatus) {

    statusLabel = tRuntime(`status.${runStatus}`, runStatus);

  }



  return (

    <div className="px-3 py-2 border-b border-default text-xs text-muted">

      {t('task.queue')}: {statusLabel}

      {workspace === 'benchmark' && benchmarkRunning && (

        <span className="ml-2 text-accent animate-pulse">{t('task.pleaseWait')}</span>

      )}

    </div>

  );

}

