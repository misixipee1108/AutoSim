import { useRef, useEffect, useState, useCallback } from 'react';
import {
  Group,
  Panel,
  Separator,
  useDefaultLayout,
  usePanelRef,
} from 'react-resizable-panels';
import { useAppStore } from '../../store/useAppStore';
import { useLocale } from '../../i18n';
import { TopToolbar } from './TopToolbar';
import { ModelTree } from '../model/ModelTree';
import { DynamicParameterForm } from '../model/DynamicParameterForm';
import { VisualizationOptionsForm } from '../model/VisualizationOptionsForm';
import { isVizOptionsPath } from '../../config/vizCatalog';
import { MainViewport } from './MainViewport';
import { SolverStatusPanel } from '../panels/SolverStatusPanel';
import { AgentDecisionPanel } from '../panels/AgentDecisionPanel';
import { ProbePanel } from '../panels/ProbePanel';
import { LogConsole } from '../logs/LogConsole';
import { CaseHistoryTable } from '../panels/CaseHistoryTable';
import { TaskQueuePanel } from '../panels/TaskQueuePanel';
import { BenchmarkReportListPanel } from '../benchmark/BenchmarkReportListPanel';
import { BenchmarkReportView } from '../benchmark/BenchmarkReportView';
import { CompareProfilesPanel } from '../panels/CompareProfilesPanel';

type Layout = { [panelId: string]: number };

const H_PANEL_IDS = ['left-params', 'center-view', 'right-status'] as const;
const V_PANEL_IDS = ['main-area', 'bottom-log'] as const;
const RIGHT_V_PANEL_IDS = ['right-solver', 'right-agent', 'right-probes'] as const;
const MIN_SIDEBAR_PCT = 12;

function layoutStorageKey(id: string, panelIds: readonly string[]) {
  return `react-resizable-panels:${id}:${panelIds.join(':')}`;
}

function clearPersistedLayout(id: string, panelIds: readonly string[]) {
  localStorage.removeItem(layoutStorageKey(id, panelIds));
}

/** Reject layouts where sidebars were saved at unusable widths (e.g. after programmatic resize). */
function sanitizeHorizontalLayout(layout: Layout | undefined): Layout | undefined {
  if (!layout) return undefined;
  const left = layout['left-params'];
  const right = layout['right-status'];
  if (left == null || right == null) return undefined;
  if (left < MIN_SIDEBAR_PCT || right < MIN_SIDEBAR_PCT) return undefined;
  return layout;
}

/** Reject layouts where bottom log was saved collapsed by a non-user resize. */
function sanitizeVerticalLayout(layout: Layout | undefined): Layout | undefined {
  if (!layout) return undefined;
  const bottom = layout['bottom-log'];
  if (bottom == null) return undefined;
  if (bottom < 2) return undefined;
  return layout;
}

function BottomDock({
  expanded,
  onToggle,
}: {
  expanded: boolean;
  onToggle: () => void;
}) {
  const { t } = useLocale();
  const logs = useAppStore((s) => s.logs);

  return (
    <div className="flex flex-col h-full min-h-0 bg-panel-solid border-t border-default">
      <div className="flex items-center justify-between px-3 py-1 border-b border-default shrink-0">
        <span className="text-xs font-medium text-muted">
          {t('panel.log')}
          {logs.length > 0 && (
            <span className="ml-2 text-faint">{t('log.count', { count: logs.length })}</span>
          )}
        </span>
        <button type="button" className="btn-ghost" onClick={onToggle}>
          {expanded ? t('log.collapse') : t('log.expand')}
        </button>
      </div>
      {expanded && (
        <div className="flex-1 min-h-0 overflow-y-auto flex flex-col">
          <TaskQueuePanel />
          <CaseHistoryTable />
          <CompareProfilesPanel />
          <LogConsole />
        </div>
      )}
    </div>
  );
}

export function AppShell() {
  const bottomPanelRef = usePanelRef();
  const initializedRef = useRef(false);
  const [logExpanded, setLogExpanded] = useState(true);
  const workspace = useAppStore((s) => s.workspace);
  const selectedTreePath = useAppStore((s) => s.selectedTreePath);
  const isBenchmark = workspace === 'benchmark';
  const showVizOptions = isVizOptionsPath(selectedTreePath);

  const { defaultLayout: vLayout, onLayoutChanged: onVLayoutChanged } = useDefaultLayout({
    id: 'autosim-layout-vertical',
    storage: localStorage,
    panelIds: [...V_PANEL_IDS],
    onlySaveAfterUserInteractions: true,
  });

  const { defaultLayout: hLayout, onLayoutChanged: onHLayoutChanged } = useDefaultLayout({
    id: 'autosim-layout-horizontal',
    storage: localStorage,
    panelIds: [...H_PANEL_IDS],
    onlySaveAfterUserInteractions: true,
  });

  const { defaultLayout: rightVLayout, onLayoutChanged: onRightVLayoutChanged } = useDefaultLayout({
    id: 'autosim-layout-right-vertical',
    storage: localStorage,
    panelIds: [...RIGHT_V_PANEL_IDS],
    onlySaveAfterUserInteractions: true,
  });

  const resolvedHLayout = sanitizeHorizontalLayout(hLayout);
  const resolvedVLayout = sanitizeVerticalLayout(vLayout);

  useEffect(() => {
    if (hLayout && !resolvedHLayout) {
      clearPersistedLayout('autosim-layout-horizontal', H_PANEL_IDS);
    }
    if (vLayout && !resolvedVLayout) {
      clearPersistedLayout('autosim-layout-vertical', V_PANEL_IDS);
    }
  }, [hLayout, vLayout, resolvedHLayout, resolvedVLayout]);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    if (resolvedVLayout) {
      setLogExpanded((resolvedVLayout['bottom-log'] ?? 0) > 5);
    } else {
      setLogExpanded(true);
    }
  }, [resolvedVLayout]);

  const toggleLog = useCallback(() => {
    const panel = bottomPanelRef.current;
    if (!panel) return;
    if (logExpanded) {
      panel.collapse();
      setLogExpanded(false);
    } else {
      panel.expand();
      setLogExpanded(true);
    }
  }, [bottomPanelRef, logExpanded]);

  return (
    <div className="flex flex-col h-screen bg-app text-primary">
      <TopToolbar />
      <Group
        orientation="vertical"
        id="autosim-vertical"
        className="flex-1 min-h-0"
        defaultLayout={resolvedVLayout}
        onLayoutChanged={onVLayoutChanged}
      >
        <Panel id="main-area" minSize="35%">
          <Group
            orientation="horizontal"
            id="autosim-horizontal"
            className="h-full"
            defaultLayout={resolvedHLayout}
            onLayoutChanged={onHLayoutChanged}
          >
            <Panel
              id="left-params"
              minSize="200px"
              maxSize="480px"
              defaultSize="288px"
              groupResizeBehavior="preserve-pixel-size"
            >
              <aside className="h-full min-h-0 flex flex-col border-r border-default bg-panel">
                {isBenchmark ? (
                  <BenchmarkReportListPanel />
                ) : (
                  <>
                    <div className="flex-1 min-h-0 overflow-y-auto">
                      <ModelTree />
                    </div>
                    <div className="flex-1 min-h-0 overflow-y-auto border-t border-default">
                      {showVizOptions ? (
                        <VisualizationOptionsForm />
                      ) : (
                        <DynamicParameterForm />
                      )}
                    </div>
                  </>
                )}
              </aside>
            </Panel>
            <Separator className="resize-handle-h" />
            <Panel id="center-view" minSize="30%">
              <main className="h-full min-w-0 flex flex-col">
                {isBenchmark ? <BenchmarkReportView /> : <MainViewport />}
              </main>
            </Panel>
            {!isBenchmark && (
              <>
            <Separator className="resize-handle-h" />
            <Panel
              id="right-status"
              minSize="200px"
              maxSize="480px"
              defaultSize="288px"
              groupResizeBehavior="preserve-pixel-size"
            >
              <aside className="h-full flex flex-col border-l border-default bg-panel min-h-0">
                <Group
                  orientation="vertical"
                  id="autosim-right-vertical"
                  className="h-full min-h-0"
                  defaultLayout={rightVLayout}
                  onLayoutChanged={onRightVLayoutChanged}
                >
                  <Panel id="right-solver" minSize="15%" defaultSize="45%">
                    <div className="h-full min-h-0 overflow-y-auto">
                      <SolverStatusPanel />
                    </div>
                  </Panel>
                  <Separator className="resize-handle-v" />
                  <Panel id="right-agent" minSize="15%" defaultSize="25%">
                    <AgentDecisionPanel />
                  </Panel>
                  <Separator className="resize-handle-v" />
                  <Panel id="right-probes" minSize="15%" defaultSize="30%">
                    <ProbePanel />
                  </Panel>
                </Group>
              </aside>
            </Panel>
              </>
            )}
          </Group>
        </Panel>
        <Separator className="resize-handle-v" />
        <Panel
          id="bottom-log"
          panelRef={bottomPanelRef}
          collapsible
          collapsedSize="32px"
          minSize="32px"
          maxSize="40%"
          defaultSize="128px"
          groupResizeBehavior="preserve-pixel-size"
          onResize={(size) => setLogExpanded(size.asPercentage > 5)}
        >
          <BottomDock expanded={logExpanded} onToggle={toggleLog} />
        </Panel>
      </Group>
    </div>
  );
}
