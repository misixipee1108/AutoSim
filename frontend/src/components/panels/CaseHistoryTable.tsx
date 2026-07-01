import { useAppStore } from '../../store/useAppStore';
import { useLocale, tRuntime, tModel } from '../../i18n';

export function CaseHistoryTable() {
  const { t } = useLocale();
  const caseHistory = useAppStore((s) => s.caseHistory);
  const setRunResult = useAppStore((s) => s.setRunResult);

  if (caseHistory.length === 0) {
    return null;
  }

  return (
    <div className="border-t border-default bg-panel px-3 py-2 max-h-32 overflow-y-auto">
      <div className="text-xs font-medium text-muted mb-1">{t('history.title')}</div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-faint">
            <th className="text-left py-0.5">{t('history.run')}</th>
            <th className="text-left">{t('history.status')}</th>
            <th className="text-left">{t('history.model')}</th>
            <th className="text-left">{t('history.compare')}</th>
          </tr>
        </thead>
        <tbody>
          {caseHistory.slice().reverse().map((c) => (
            <tr key={c.run_id} className="border-t border-subtle">
              <td className="py-0.5 font-mono text-muted">{c.run_id.slice(0, 8)}</td>
              <td className="text-primary">{tRuntime(`status.${c.status}`, c.status)}</td>
              <td className="text-primary">{tModel(c.model_id, 'name', c.model_id)}</td>
              <td>
                <button
                  type="button"
                  className="text-accent hover:underline"
                  onClick={() => setRunResult(c)}
                >
                  {t('history.view')}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
