import { create } from 'zustand';
import type {
  BenchmarkReport,
  BenchmarkReportListItem,
  ConvergenceSeries,
  ModelTreeSchema,
  ParameterSchema,
  ProjectTemplateListItem,
  RunStatus,
  SimulationProject,
  UnifiedAgentDecision,
  UnifiedProbe,
  UnifiedRunResult,
  Workspace,
} from '../types';
import { createSimApi, FALLBACK_PROJECT_TEMPLATES, getMockProjectTemplate, probeLiveApi } from '../api/client';
import { t, tRuntime, resolveAgentReason } from '../i18n';
import { buildMockProjectTree } from '../mocks/projectTree';
import {
  findFirstSelectableTreePath,
  resolveProjectParameters,
  setProjectValue as applyProjectValue,
} from '../utils/projectParameters';
import { buildChartTabs, resolveActiveChartTab, firstProfileTabId } from '../utils/buildChartTabs';
import {
  buildDefaultChartGroups,
  canMergeVizIds,
  getDefaultEnabledVizIds,
  getEnabledProfileSeries,
  shouldFocusConvergenceTab,
  syncChartGroupsOnToggle,
  type VizLayoutMode,
} from '../config/vizCatalog';
import { inferModelIdFromProject } from '../i18n/resolveLabels';

const PROBE_TO_CONVERGENCE: Record<string, string> = {
  residual_norm: 'residual',
  scaled_residual_norm: 'scaled_residual',
  scaled_delta_norm: 'scaled_delta',
  energy_drift: 'energy_drift',
};

function appendProbeToConvergence(
  conv: ConvergenceSeries[],
  probe: UnifiedProbe,
): ConvergenceSeries[] {
  const seriesName = PROBE_TO_CONVERGENCE[probe.name];
  if (!seriesName || !probe.x?.length) return conv;
  const yValues = probe.y?.length
    ? probe.y
    : probe.x.map(() => Number(probe.value ?? 0));
  const existing = conv.find((c) => c.name === seriesName);
  if (existing) {
    return conv.map((c) =>
      c.name === seriesName
        ? { ...c, x: [...c.x, ...probe.x!], y: [...c.y, ...yValues] }
        : c,
    );
  }
  return [
    ...conv,
    {
      name: seriesName,
      label: probe.label,
      unit: probe.unit ?? '',
      x: [...probe.x],
      y: [...yValues],
      x_label: tRuntime('series.Iteration', 'Iteration'),
    },
  ];
}

export type ApiMode = 'mock' | 'live';

interface AppState {
  apiMode: ApiMode;
  projectTemplates: ProjectTemplateListItem[];
  currentTemplateId: string;
  currentProject: SimulationProject | null;
  projectTreeSchema: ModelTreeSchema | null;
  projectParameters: ParameterSchema[];
  selectedTreePath: string | null;
  runId: string | null;
  runStatus: RunStatus | null;
  runResult: UnifiedRunResult | null;
  liveProbes: UnifiedProbe[];
  liveDecisions: UnifiedAgentDecision[];
  logs: string[];
  activeChartTab: string;
  isRunning: boolean;
  agentBackend: string;
  caseHistory: UnifiedRunResult[];
  workspace: Workspace;
  benchmarkReports: BenchmarkReportListItem[];
  selectedBenchmarkRunId: string | null;
  benchmarkReport: BenchmarkReport | null;
  benchmarkMarkdown: string | null;
  benchmarkLoading: boolean;
  benchmarkError: string | null;
  benchmarkRunning: boolean;
  compareRunIds: string[];
  liveApiReachable: boolean | null;
  enabledVizIds: string[];
  chartReplayKey: number;
  autoFocusChartOnComplete: boolean;
  vizLayoutMode: VizLayoutMode;
  vizChartGroups: string[][];

  setApiMode: (mode: ApiMode) => void;
  setWorkspace: (workspace: Workspace) => void;
  loadBenchmarkReports: () => Promise<void>;
  runBenchmarkSuite: () => Promise<void>;
  selectBenchmarkReport: (runId: string) => Promise<void>;
  toggleCompareRun: (runId: string) => void;
  clearCompareRuns: () => void;
  loadProjectTemplates: () => Promise<void>;
  loadProjectTemplate: (templateId?: string) => Promise<void>;
  importProject: (project: SimulationProject) => void;
  setProjectValue: (path: string, value: unknown) => void;
  setSelectedTreePath: (path: string) => void;
  setActiveChartTab: (tabId: string) => void;
  setAgentBackend: (backend: string) => void;
  setRunResult: (result: UnifiedRunResult | null) => void;
  startRun: () => Promise<void>;
  stopRun: () => void;
  appendLog: (msg: string) => void;
  updateFromStream: (partial: Partial<UnifiedRunResult>) => void;
  initEnabledVizFromCatalog: (modelId?: string) => void;
  toggleVizOption: (id: string) => void;
  setEnabledVizIds: (ids: string[]) => void;
  setVizLayoutMode: (mode: VizLayoutMode) => void;
  setVizChartGroups: (groups: string[][]) => void;
  mergeSelectedVizIds: (vizIds: string[]) => boolean;
  splitVizToOwnGroup: (vizId: string) => void;
}

let unsubscribeStream: (() => void) | null = null;
let liveApiProbePromise: Promise<boolean> | null = null;
const projectTemplateCache = new Map<string, SimulationProject>();

async function ensureLiveApiReachable(
  get: () => AppState,
  set: (partial: Partial<AppState>) => void,
): Promise<boolean> {
  if (get().apiMode !== 'live') return true;
  if (get().liveApiReachable === false) return false;
  if (get().liveApiReachable === true) return true;
  if (!liveApiProbePromise) {
    liveApiProbePromise = probeLiveApi().then((ok) => {
      set({ liveApiReachable: ok });
      liveApiProbePromise = null;
      return ok;
    });
  }
  return liveApiProbePromise;
}

async function resolveEffectiveApiMode(
  get: () => AppState,
  set: (partial: Partial<AppState>) => void,
): Promise<ApiMode> {
  if (get().apiMode !== 'live') return 'mock';
  const reachable = await ensureLiveApiReachable(get, set);
  return reachable ? 'live' : 'mock';
}

async function fetchProjectParameters(
  project: SimulationProject,
  treePath: string,
  get: () => AppState,
  set: (partial: Partial<AppState>) => void,
): Promise<ParameterSchema[]> {
  const effectiveMode = await resolveEffectiveApiMode(get, set);
  if (effectiveMode === 'live') {
    try {
      const resp = await createSimApi('live').getProjectParameters(project, treePath);
      return resp.parameters;
    } catch {
      // Fall back to client-side schema when the API is unavailable.
    }
  }
  return resolveProjectParameters(project, treePath);
}

async function applyProjectToStore(
  project: SimulationProject,
  apiMode: ApiMode,
  set: (partial: Partial<AppState>) => void,
  get: () => AppState,
) {
  const treeSchema =
    apiMode === 'mock'
      ? buildMockProjectTree(project)
      : await createSimApi('live').getProjectTreeSchema(project);
  const firstPath = findFirstSelectableTreePath(treeSchema);
  const params = await fetchProjectParameters(project, firstPath, get, set);
  const modelId = inferModelIdFromProject(project);
  const enabledVizIds = getDefaultEnabledVizIds(modelId);
  const vizLayoutMode: VizLayoutMode = 'separate_tabs';
  const vizChartGroups = buildDefaultChartGroups(modelId, enabledVizIds);
  const chartTabs = buildChartTabs(
    project,
    enabledVizIds,
    modelId,
    vizLayoutMode,
    vizChartGroups,
  );
  set({
    currentProject: project,
    projectTreeSchema: treeSchema,
    selectedTreePath: firstPath,
    projectParameters: params,
    enabledVizIds,
    vizLayoutMode,
    vizChartGroups,
    chartReplayKey: 0,
    activeChartTab: chartTabs[0]?.id ?? 'overview',
    runId: null,
    runStatus: null,
    runResult: null,
    liveProbes: [],
    liveDecisions: [],
    logs: [],
    isRunning: false,
  });
}

async function loadProjectForMode(
  templateId: string,
  apiMode: ApiMode,
  set: (partial: Partial<AppState>) => void,
  get: () => AppState,
) {
  const project =
    apiMode === 'mock'
      ? getMockProjectTemplate(templateId)
      : await createSimApi('live').getProjectTemplate(templateId);
  projectTemplateCache.set(templateId, structuredClone(project));
  await applyProjectToStore(project, apiMode, set, get);
}

export const useAppStore = create<AppState>((set, get) => ({
  apiMode: (import.meta.env.VITE_API_MODE as ApiMode) ?? 'mock',
  projectTemplates: [],
  currentTemplateId: 'pn_stationary',
  currentProject: null,
  projectTreeSchema: null,
  projectParameters: [],
  selectedTreePath: null,
  runId: null,
  runStatus: null,
  runResult: null,
  liveProbes: [],
  liveDecisions: [],
  logs: [],
  activeChartTab: 'overview',
  isRunning: false,
  agentBackend: 'rules',
  caseHistory: [],
  workspace: 'simulation',
  benchmarkReports: [],
  selectedBenchmarkRunId: null,
  benchmarkReport: null,
  benchmarkMarkdown: null,
  benchmarkLoading: false,
  benchmarkError: null,
  benchmarkRunning: false,
  compareRunIds: [],
  liveApiReachable: null,
  enabledVizIds: [],
  chartReplayKey: 0,
  autoFocusChartOnComplete: true,
  vizLayoutMode: 'separate_tabs',
  vizChartGroups: [],

  setApiMode: (mode) => {
    set({ apiMode: mode, liveApiReachable: mode === 'live' ? null : true });
    projectTemplateCache.clear();
    void Promise.allSettled([
      get().loadProjectTemplates(),
      get().loadProjectTemplate(get().currentTemplateId),
    ]);
    if (get().workspace === 'benchmark') {
      get().loadBenchmarkReports();
    }
  },

  setWorkspace: (workspace) => {
    set({ workspace });
    if (workspace === 'benchmark') {
      get().loadBenchmarkReports();
    }
  },

  loadBenchmarkReports: async () => {
    set({ benchmarkLoading: true, benchmarkError: null });
    try {
      const api = createSimApi(get().apiMode);
      const reports = await api.listBenchmarkReports();
      set({ benchmarkReports: reports, benchmarkLoading: false });
      const selected = get().selectedBenchmarkRunId;
      if (reports.length > 0) {
        const target = selected && reports.some((r) => r.run_id === selected)
          ? selected
          : reports[0].run_id;
        if (target !== selected || !get().benchmarkReport) {
          await get().selectBenchmarkReport(target);
        }
      } else {
        set({ benchmarkReport: null, benchmarkMarkdown: null, selectedBenchmarkRunId: null });
      }
    } catch (err) {
      set({
        benchmarkLoading: false,
        benchmarkError: err instanceof Error ? err.message : String(err),
      });
      get().appendLog(t('benchmark.loadFailed', { message: String(err) }));
    }
  },

  selectBenchmarkReport: async (runId) => {
    set({ benchmarkLoading: true, benchmarkError: null, selectedBenchmarkRunId: runId });
    try {
      const api = createSimApi(get().apiMode);
      const [report, markdown] = await Promise.all([
        api.getBenchmarkReport(runId),
        api.getBenchmarkReportMarkdown(runId),
      ]);
      set({ benchmarkReport: report, benchmarkMarkdown: markdown, benchmarkLoading: false });
      get().appendLog(t('benchmark.loaded', { runId: report.run_id }));
    } catch (err) {
      set({
        benchmarkLoading: false,
        benchmarkError: err instanceof Error ? err.message : String(err),
      });
    }
  },

  runBenchmarkSuite: async () => {
    set({ benchmarkRunning: true, benchmarkError: null });
    get().appendLog(t('benchmark.running'));
    try {
      const api = createSimApi(get().apiMode);
      const result = await api.runBenchmarkSuite();
      get().appendLog(
        t('benchmark.runComplete', {
          runId: result.run_id,
          passed: result.passed_count,
          total: result.total,
        }),
      );
      await get().loadBenchmarkReports();
      await get().selectBenchmarkReport(result.run_id);
    } catch (err) {
      set({
        benchmarkError: err instanceof Error ? err.message : String(err),
      });
      get().appendLog(t('benchmark.runFailed', { message: String(err) }));
    } finally {
      set({ benchmarkRunning: false });
    }
  },

  toggleCompareRun: (runId) => {
    set((s) => {
      const ids = s.compareRunIds.includes(runId)
        ? s.compareRunIds.filter((id) => id !== runId)
        : s.compareRunIds.length >= 4
          ? [...s.compareRunIds.slice(1), runId]
          : [...s.compareRunIds, runId];
      return { compareRunIds: ids };
    });
  },

  clearCompareRuns: () => set({ compareRunIds: [] }),

  loadProjectTemplates: async () => {
    const uiMode = await resolveEffectiveApiMode(get, set);
    if (uiMode === 'mock') {
      set({ projectTemplates: FALLBACK_PROJECT_TEMPLATES });
      return;
    }
    try {
      const templates = await createSimApi('live').listProjectTemplates();
      set({ projectTemplates: templates });
    } catch (err) {
      set({ projectTemplates: FALLBACK_PROJECT_TEMPLATES, liveApiReachable: false });
      if (get().apiMode === 'live') {
        get().appendLog(t('log.liveApiFallbackTemplates', { detail: String(err) }));
      }
    }
  },

  loadProjectTemplate: async (templateId) => {
    if (unsubscribeStream) {
      unsubscribeStream();
      unsubscribeStream = null;
    }
    const tid = templateId ?? get().currentTemplateId ?? 'pn_stationary';
    const cached = projectTemplateCache.get(tid);
    if (cached) {
      await applyProjectToStore(cached, 'mock', set, get);
      set({ currentTemplateId: tid });
      return;
    }
    const uiMode = await resolveEffectiveApiMode(get, set);
    try {
      await loadProjectForMode(tid, uiMode, set, get);
      set({ currentTemplateId: tid });
    } catch (err) {
      if (get().apiMode === 'live' && uiMode === 'live') {
        set({ liveApiReachable: false });
        try {
          await loadProjectForMode(tid, 'mock', set, get);
          if (get().projectTemplates.length === 0) {
            set({ projectTemplates: FALLBACK_PROJECT_TEMPLATES });
          }
          set({ currentTemplateId: tid });
          get().appendLog(t('log.liveApiFallbackTemplate', { id: tid, detail: String(err) }));
          return;
        } catch (mockErr) {
          err = mockErr;
        }
      }
      get().appendLog(t('log.failedStart', { message: String(err) }));
    }
  },

  importProject: (project) => {
    if (unsubscribeStream) {
      unsubscribeStream();
      unsubscribeStream = null;
    }
    void applyProjectToStore(project, get().apiMode, set, get);
  },

  setProjectValue: (path, value) => {
    const project = get().currentProject;
    if (!project) return;
    const updated = applyProjectValue(project, path, value);
    set({ currentProject: updated });
  },

  setSelectedTreePath: (path) => {
    const project = get().currentProject;
    set({ selectedTreePath: path });
    if (!project) return;
    void fetchProjectParameters(project, path, get, set).then((params) => {
      if (get().selectedTreePath === path) {
        set({ projectParameters: params });
      }
    });
  },

  setActiveChartTab: (tabId) => set({ activeChartTab: tabId }),

  setAgentBackend: (backend) => set({ agentBackend: backend }),

  setRunResult: (result) => set({ runResult: result }),

  initEnabledVizFromCatalog: (modelId) => {
    const project = get().currentProject;
    const mid = (modelId ?? inferModelIdFromProject(project)) as ReturnType<
      typeof inferModelIdFromProject
    >;
    const ids = getDefaultEnabledVizIds(mid);
    set({
      enabledVizIds: ids,
      vizChartGroups: buildDefaultChartGroups(mid, ids),
    });
  },

  setEnabledVizIds: (ids) => {
    const modelId = inferModelIdFromProject(get().currentProject);
    set({
      enabledVizIds: ids,
      vizChartGroups: buildDefaultChartGroups(modelId, ids),
    });
  },

  setVizLayoutMode: (mode) => {
    set((s) => {
      const modelId = inferModelIdFromProject(s.currentProject);
      const tabs = s.currentProject
        ? buildChartTabs(
            s.currentProject,
            s.enabledVizIds,
            modelId,
            mode,
            s.vizChartGroups,
          )
        : [];
      return {
        vizLayoutMode: mode,
        activeChartTab: resolveActiveChartTab(tabs, s.activeChartTab),
      };
    });
  },

  setVizChartGroups: (groups) => set({ vizChartGroups: groups }),

  mergeSelectedVizIds: (vizIds) => {
    if (vizIds.length < 2) return false;
    const modelId = inferModelIdFromProject(get().currentProject);
    if (!canMergeVizIds(modelId, vizIds)) return false;
    const merged = [...new Set(vizIds)];
    set((s) => {
      const groups = s.vizChartGroups
        .map((g) => g.filter((id) => !merged.includes(id)))
        .filter((g) => g.length > 0);
      groups.push(merged);
      return { vizChartGroups: groups };
    });
    return true;
  },

  splitVizToOwnGroup: (vizId) => {
    set((s) => {
      const groups = s.vizChartGroups
        .map((g) => g.filter((x) => x !== vizId))
        .filter((g) => g.length > 0);
      if (!s.enabledVizIds.includes(vizId)) return s;
      return { vizChartGroups: [...groups, [vizId]] };
    });
  },

  toggleVizOption: (id) => {
    set((s) => {
      const enabling = !s.enabledVizIds.includes(id);
      const next = enabling
        ? [...s.enabledVizIds, id]
        : s.enabledVizIds.filter((x) => x !== id);
      const modelId = inferModelIdFromProject(s.currentProject);
      const nextGroups = syncChartGroupsOnToggle(
        s.vizChartGroups,
        id,
        enabling,
        modelId,
      );
      const tabs = s.currentProject
        ? buildChartTabs(
            s.currentProject,
            next,
            modelId,
            s.vizLayoutMode,
            nextGroups,
          )
        : [];
      return {
        enabledVizIds: next,
        vizChartGroups: nextGroups,
        activeChartTab: resolveActiveChartTab(tabs, s.activeChartTab),
      };
    });
  },

  appendLog: (msg) => set((s) => ({ logs: [...s.logs, msg] })),

  updateFromStream: (partial) => {
    set((s) => ({
      runResult: s.runResult ? { ...s.runResult, ...partial } : (partial as UnifiedRunResult),
      liveProbes: partial.probes ?? s.liveProbes,
      liveDecisions: partial.decisions ?? s.liveDecisions,
    }));
  },

  startRun: async () => {
    const { currentProject, agentBackend } = get();
    if (!currentProject) return;

    if (unsubscribeStream) {
      unsubscribeStream();
      unsubscribeStream = null;
    }

    const studyParams = (currentProject.studies?.[0]?.parameters ?? {}) as Record<string, unknown>;
    const iteration = studyParams['iteration'] as { max_trials?: number } | undefined;
    const maxTrials = iteration?.max_trials ?? 1;
    const runRequest = {
      project: currentProject as unknown as Record<string, unknown>,
      active_study_id: currentProject.active_study_id,
      agent: agentBackend,
      max_trials: maxTrials,
    };

    set({
      isRunning: true,
      runStatus: 'running',
      runResult: null,
      liveProbes: [],
      liveDecisions: [],
      logs: [t('log.starting', { modelId: currentProject.project_id })],
    });

    const subscribeToRun = (api: ReturnType<typeof createSimApi>, created: { run_id: string; model_id: string }) => {
      const resultModelId = created.model_id;
      set({ runId: created.run_id, runStatus: 'running' });

      unsubscribeStream = api.subscribeRun(created.run_id, {
        onLog: (msg) => get().appendLog(msg),
        onStatus: (status) => set({ runStatus: status }),
        onProbe: (probe) => {
          set((s) => {
            const conv = s.runResult?.convergence ?? [];
            const updatedConv = appendProbeToConvergence(conv, probe);
            const prevProbes = s.runResult?.probes ?? s.liveProbes ?? [];
            const byName = new Map(prevProbes.map((p) => [p.name, p]));
            byName.set(probe.name, probe);
            const mergedProbes = Array.from(byName.values());
            return {
              liveProbes: mergedProbes,
              runResult: s.runResult
                ? { ...s.runResult, probes: mergedProbes, convergence: updatedConv }
                : {
                    run_id: created.run_id,
                    model_id: resultModelId,
                    status: 'running' as RunStatus,
                    trial_index: 0,
                    scalars: {},
                    profiles: [],
                    time_series: [],
                    sweep: [],
                    convergence: updatedConv,
                    probes: mergedProbes,
                    decisions: [],
                    logs: s.logs,
                    trials: [],
                  },
            };
          });
        },
        onDecision: (decision) => {
          set((s) => ({
            liveDecisions: [...s.liveDecisions, decision],
            runResult: s.runResult
              ? { ...s.runResult, decisions: [...(s.runResult.decisions ?? []), decision] }
              : null,
          }));
          get().appendLog(
            t('log.agentDecision', {
              action: tRuntime(`action.${decision.action}`, decision.action),
              reason: resolveAgentReason(decision.reason),
            }),
          );
        },
        onComplete: (result) => {
          set((s) => {
            const modelId = inferModelIdFromProject(s.currentProject);
            const profileSeries = getEnabledProfileSeries(modelId, s.enabledVizIds);
            let activeChartTab = s.activeChartTab;
            if (s.autoFocusChartOnComplete) {
              const solverStatus = result.solver_status ?? result.status;
              if (shouldFocusConvergenceTab(solverStatus)) {
                activeChartTab = 'convergence';
              } else if (profileSeries.length > 0) {
                activeChartTab =
                  firstProfileTabId(s.enabledVizIds, modelId, s.vizLayoutMode) ??
                  'profiles';
              }
            }
            return {
              runResult: result,
              runStatus: result.status,
              isRunning: false,
              caseHistory: [...s.caseHistory, result].slice(-20),
              chartReplayKey: s.chartReplayKey + 1,
              activeChartTab,
            };
          });
          get().appendLog(t('log.complete'));
        },
        onError: (error) => {
          set({ isRunning: false, runStatus: 'failed' });
          get().appendLog(t('log.error', { error }));
        },
      });
    };

    let runApiMode = await resolveEffectiveApiMode(get, set);
    if (get().apiMode === 'live' && runApiMode === 'mock') {
      get().appendLog(t('log.liveApiFallbackRun'));
    }

    try {
      const api = createSimApi(runApiMode);
      const created = await api.createRun(runRequest);
      subscribeToRun(api, created);
    } catch (err) {
      if (get().apiMode === 'live' && runApiMode === 'live') {
        set({ liveApiReachable: false });
        runApiMode = 'mock';
        get().appendLog(t('log.liveApiFallbackRun'));
        try {
          const mockApi = createSimApi('mock');
          const created = await mockApi.createRun(runRequest);
          subscribeToRun(mockApi, created);
          return;
        } catch (mockErr) {
          err = mockErr;
        }
      }
      set({ isRunning: false, runStatus: 'failed' });
      get().appendLog(
        t('log.failedStart', {
          message: err instanceof Error ? err.message : String(err),
        }),
      );
    }
  },

  stopRun: () => {
    if (unsubscribeStream) {
      unsubscribeStream();
      unsubscribeStream = null;
    }
    set({ isRunning: false, runStatus: 'early_stopped' });
    get().appendLog(t('log.stopped'));
  },
}));
