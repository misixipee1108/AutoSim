import { useMemo } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { ChartRouter } from '../charts/ChartRouter';
import { useLocale, inferModelIdFromProject } from '../../i18n';
import { buildChartTabs } from '../../utils/buildChartTabs';

export function MainViewport() {
  const { t } = useLocale();
  const currentProject = useAppStore((s) => s.currentProject);
  const activeTab = useAppStore((s) => s.activeChartTab);
  const setActiveTab = useAppStore((s) => s.setActiveChartTab);
  const runResult = useAppStore((s) => s.runResult);
  const enabledVizIds = useAppStore((s) => s.enabledVizIds);
  const vizLayoutMode = useAppStore((s) => s.vizLayoutMode);
  const vizChartGroups = useAppStore((s) => s.vizChartGroups);

  const modelId = currentProject ? inferModelIdFromProject(currentProject) : undefined;

  const tabs = useMemo(() => {
    if (!currentProject || !modelId) return [];
    return buildChartTabs(
      currentProject,
      enabledVizIds,
      modelId,
      vizLayoutMode,
      vizChartGroups,
    );
  }, [currentProject, enabledVizIds, modelId, vizLayoutMode, vizChartGroups]);

  const active = tabs.find((tab) => tab.id === activeTab) ?? tabs[0];

  if (!currentProject) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted">
        {t('viewport.loadingModel')}
      </div>
    );
  }

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
            {tab.label}
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
