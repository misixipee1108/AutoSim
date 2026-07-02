import { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import {
  findVizGroupIndex,
  getCatalogItem,
  getEnabledProfileVizIds,
  getVizCatalog,
  type VizCatalogItem,
  type VizGroup,
} from '../../config/vizCatalog';
import {
  useLocale,
  inferModelIdFromProject,
  tModel,
} from '../../i18n';
import { DelayedTooltip } from '../ui/DelayedTooltip';

function VizCheckbox({
  item,
  modelId,
  checked,
  onToggle,
}: {
  item: VizCatalogItem;
  modelId: ReturnType<typeof inferModelIdFromProject>;
  checked: boolean;
  onToggle: () => void;
}) {
  const label =
    tModel(modelId, `vizOptions.${item.i18nKey}.label`, item.i18nKey) ??
    item.i18nKey;
  const description = tModel(
    modelId,
    `vizOptions.${item.i18nKey}.description`,
    '',
  );

  return (
    <label className="flex items-start gap-2 py-1.5 cursor-pointer group">
      <input
        type="checkbox"
        checked={checked}
        onChange={onToggle}
        className="mt-0.5 shrink-0"
      />
      <span className="flex flex-col gap-0.5 min-w-0">
        <DelayedTooltip content={description} disabled={!description}>
          <span className="text-xs text-primary group-hover:text-accent cursor-help">
            {label}
          </span>
        </DelayedTooltip>
      </span>
    </label>
  );
}

function VizGroupSection({
  title,
  items,
  modelId,
  enabledVizIds,
  onToggle,
}: {
  title: string;
  items: VizCatalogItem[];
  modelId: ReturnType<typeof inferModelIdFromProject>;
  enabledVizIds: string[];
  onToggle: (id: string) => void;
}) {
  if (!items.length) return null;
  return (
    <div className="mb-3">
      <div className="text-[10px] uppercase tracking-wide text-faint mb-1 px-1">
        {title}
      </div>
      <div className="flex flex-col px-1">
        {items.map((item) => (
          <VizCheckbox
            key={item.id}
            item={item}
            modelId={modelId}
            checked={enabledVizIds.includes(item.id)}
            onToggle={() => onToggle(item.id)}
          />
        ))}
      </div>
    </div>
  );
}

const GROUP_I18N: Record<VizGroup, string> = {
  profile: 'vizOptions.groupProfiles',
  convergence: 'vizOptions.groupConvergence',
  time_series: 'vizOptions.groupTimeSeries',
};

export function VisualizationOptionsForm() {
  const { t } = useLocale();
  const project = useAppStore((s) => s.currentProject);
  const enabledVizIds = useAppStore((s) => s.enabledVizIds);
  const vizLayoutMode = useAppStore((s) => s.vizLayoutMode);
  const vizChartGroups = useAppStore((s) => s.vizChartGroups);
  const toggleVizOption = useAppStore((s) => s.toggleVizOption);
  const setVizLayoutMode = useAppStore((s) => s.setVizLayoutMode);
  const mergeSelectedVizIds = useAppStore((s) => s.mergeSelectedVizIds);
  const splitVizToOwnGroup = useAppStore((s) => s.splitVizToOwnGroup);
  const isRunning = useAppStore((s) => s.isRunning);
  const [mergeSelection, setMergeSelection] = useState<string[]>([]);
  const [mergeError, setMergeError] = useState<string | null>(null);

  if (!project) {
    return (
      <div className="p-3 text-xs text-muted">{t('panel.loadingProject')}</div>
    );
  }

  const modelId = inferModelIdFromProject(project);
  const catalog = getVizCatalog(modelId);
  const profileItems = catalog.filter((c) => c.group === 'profile');
  const profileVizIds = getEnabledProfileVizIds(modelId, enabledVizIds);
  const convergenceItems = catalog.filter((c) => c.group === 'convergence');
  const timeSeriesItems = catalog.filter((c) => c.group === 'time_series');

  const toggleMergeSelect = (vizId: string) => {
    setMergeError(null);
    setMergeSelection((prev) =>
      prev.includes(vizId) ? prev.filter((x) => x !== vizId) : [...prev, vizId],
    );
  };

  const handleMerge = () => {
    if (mergeSelection.length < 2) return;
    const ok = mergeSelectedVizIds(mergeSelection);
    if (!ok) {
      setMergeError(t('vizOptions.mergeIncompatible'));
      return;
    }
    setMergeSelection([]);
    setMergeError(null);
  };

  return (
    <div className="p-3 flex flex-col h-full min-h-0">
      <h3 className="text-xs font-medium text-muted mb-2 shrink-0">
        {t('vizOptions.title')}
      </h3>

      <div className="mb-3 shrink-0">
        <div className="text-[10px] uppercase tracking-wide text-faint mb-1.5 px-1">
          {t('vizOptions.layoutMode')}
        </div>
        <div className="flex gap-1 px-1">
          <button
            type="button"
            className={`flex-1 text-[11px] py-1 px-2 rounded border ${
              vizLayoutMode === 'separate_tabs'
                ? 'tab-btn-active border-accent'
                : 'border-default text-muted'
            }`}
            onClick={() => setVizLayoutMode('separate_tabs')}
          >
            {t('vizOptions.layoutSeparate')}
          </button>
          <button
            type="button"
            className={`flex-1 text-[11px] py-1 px-2 rounded border ${
              vizLayoutMode === 'combined'
                ? 'tab-btn-active border-accent'
                : 'border-default text-muted'
            }`}
            onClick={() => setVizLayoutMode('combined')}
          >
            {t('vizOptions.layoutCombined')}
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        <VizGroupSection
          title={t(GROUP_I18N.profile)}
          items={profileItems}
          modelId={modelId}
          enabledVizIds={enabledVizIds}
          onToggle={toggleVizOption}
        />

        {vizLayoutMode === 'combined' && profileVizIds.length >= 2 && (
          <div className="mb-3 px-1 border-t border-default pt-2">
            <div className="text-[10px] uppercase tracking-wide text-faint mb-1.5">
              {t('vizOptions.mergeSection')}
            </div>
            <p className="text-[10px] text-faint mb-2">{t('vizOptions.mergeHint')}</p>
            <div className="flex flex-col gap-1 mb-2">
              {profileVizIds.map((vizId) => {
                const item = getCatalogItem(modelId, vizId);
                if (!item) return null;
                const groupIdx = findVizGroupIndex(vizChartGroups, vizId);
                const groupLabel =
                  groupIdx >= 0
                    ? t('vizOptions.chartGroup', { n: groupIdx + 1 })
                    : '—';
                const label = tModel(
                  modelId,
                  `vizOptions.${item.i18nKey}.label`,
                  item.i18nKey,
                );
                return (
                  <div
                    key={vizId}
                    className="flex items-center gap-2 text-xs py-0.5"
                  >
                    <input
                      type="checkbox"
                      checked={mergeSelection.includes(vizId)}
                      onChange={() => toggleMergeSelect(vizId)}
                    />
                    <span className="flex-1 text-primary truncate">{label}</span>
                    <span className="text-[10px] text-faint shrink-0">{groupLabel}</span>
                    {groupIdx >= 0 && vizChartGroups[groupIdx]?.length > 1 && (
                      <button
                        type="button"
                        className="text-[10px] text-accent shrink-0"
                        onClick={() => splitVizToOwnGroup(vizId)}
                      >
                        {t('vizOptions.splitGroup')}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
            <button
              type="button"
              className="btn-ghost text-xs w-full"
              disabled={mergeSelection.length < 2}
              onClick={handleMerge}
            >
              {t('vizOptions.mergeSelected')}
            </button>
            {mergeError && (
              <p className="text-[10px] text-error mt-1">{mergeError}</p>
            )}
          </div>
        )}

        <VizGroupSection
          title={t(GROUP_I18N.convergence)}
          items={[...convergenceItems, ...timeSeriesItems]}
          modelId={modelId}
          enabledVizIds={enabledVizIds}
          onToggle={toggleVizOption}
        />
      </div>
      <p className="text-[10px] text-faint mt-2 shrink-0 border-t border-default pt-2">
        {isRunning ? t('vizOptions.hintRunning') : t('vizOptions.hintIdle')}
      </p>
    </div>
  );
}
