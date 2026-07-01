import { useAppStore } from '../../store/useAppStore';
import { ChartRouter } from '../charts/ChartRouter';
import { useLocale, tModel } from '../../i18n';

export function MainViewport() {
  const { t } = useLocale();
  const descriptor = useAppStore((s) => s.currentDescriptor);
  const activeTab = useAppStore((s) => s.activeChartTab);
  const setActiveTab = useAppStore((s) => s.setActiveChartTab);
  const runResult = useAppStore((s) => s.runResult);

  if (!descriptor) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted">
        {t('viewport.loadingModel')}
      </div>
    );
  }

  const tabs = descriptor.default_charts;
  const active = tabs.find((tab) => tab.id === activeTab) ?? tabs[0];

  return (
    <div className="flex flex-col flex-1 min-h-0 h-full">
      {runResult?.error && (
        <div className="px-4 py-2 error-banner text-xs shrink-0">
          {runResult.error}
        </div>
      )}
      <div className="tab-bar flex shrink-0">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`tab-btn ${activeTab === tab.id ? 'tab-btn-active' : ''}`}
          >
            {tModel(descriptor.model_id, `charts.${tab.id}`, tab.label)}
          </button>
        ))}
      </div>
      <div className="flex-1 p-3 min-h-0 overflow-hidden">
        {!runResult && active?.chart_type !== 'overview' ? (
          <div className="flex items-center justify-center h-full text-muted text-sm">
            {t('viewport.runToView')}
          </div>
        ) : active ? (
          <ChartRouter tab={active} />
        ) : null}
      </div>
    </div>
  );
}
