import { create } from 'zustand';
import type {
  ConvergenceSeries,
  ModelDescriptor,
  RunStatus,
  UnifiedAgentDecision,
  UnifiedProbe,
  UnifiedRunResult,
} from '../types';
import { createSimApi } from '../api/client';
import { t, tRuntime } from '../i18n';

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
      x_label: 'Iteration',
    },
  ];
}

export type ApiMode = 'mock' | 'live';

interface AppState {
  apiMode: ApiMode;
  models: ModelDescriptor[];
  currentModelId: string | null;
  currentDescriptor: ModelDescriptor | null;
  config: Record<string, unknown>;
  selectedTreeNode: string | null;
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
  quantityDisplay: Record<string, string>;

  setApiMode: (mode: ApiMode) => void;
  loadModels: () => Promise<void>;
  selectModel: (modelId: string) => Promise<void>;
  setConfigValue: (name: string, value: unknown) => void;
  setConfig: (config: Record<string, unknown>) => void;
  setQuantityDisplay: (name: string, text: string) => void;
  setSelectedTreeNode: (nodeId: string) => void;
  setActiveChartTab: (tabId: string) => void;
  setAgentBackend: (backend: string) => void;
  setRunResult: (result: UnifiedRunResult | null) => void;
  startRun: () => Promise<void>;
  stopRun: () => void;
  appendLog: (msg: string) => void;
  updateFromStream: (partial: Partial<UnifiedRunResult>) => void;
}

function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  const parts = path.split('.');
  let cur: unknown = obj;
  for (const p of parts) {
    if (cur == null || typeof cur !== 'object') return undefined;
    cur = (cur as Record<string, unknown>)[p];
  }
  return cur;
}

function buildQuantityDisplay(
  descriptor: ModelDescriptor,
  config: Record<string, unknown>,
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const p of descriptor.parameters) {
    if (!p.unit) continue;
    const v = getNestedValue(config, p.name);
    if (typeof v === 'number') {
      out[p.name] = `${v}[${p.unit}]`;
    }
  }
  return out;
}

function setNested(obj: Record<string, unknown>, path: string, value: unknown): Record<string, unknown> {
  const parts = path.split('.');
  const result = { ...obj };
  let cursor: Record<string, unknown> = result;
  for (let i = 0; i < parts.length - 1; i++) {
    cursor[parts[i]] = { ...(cursor[parts[i]] as Record<string, unknown> ?? {}) };
    cursor = cursor[parts[i]] as Record<string, unknown>;
  }
  cursor[parts[parts.length - 1]] = value;
  return result;
}

let unsubscribeStream: (() => void) | null = null;

export const useAppStore = create<AppState>((set, get) => ({
  apiMode: (import.meta.env.VITE_API_MODE as ApiMode) ?? 'mock',
  models: [],
  currentModelId: null,
  currentDescriptor: null,
  config: {},
  selectedTreeNode: null,
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
  quantityDisplay: {},

  setApiMode: (mode) => {
    set({ apiMode: mode });
    const modelId = get().currentModelId;
    get().loadModels().then(() => {
      if (modelId) {
        get().selectModel(modelId);
      }
    });
  },

  loadModels: async () => {
    const api = createSimApi(get().apiMode);
    const models = await api.listModels();
    set({ models });
    if (models.length > 0 && !get().currentModelId) {
      await get().selectModel(models[0].model_id);
    }
  },

  selectModel: async (modelId) => {
    if (unsubscribeStream) {
      unsubscribeStream();
      unsubscribeStream = null;
    }
    const api = createSimApi(get().apiMode);
    const descriptor = await api.getModel(modelId);
    const config = { ...descriptor.default_config };
    set({
      currentModelId: modelId,
      currentDescriptor: descriptor,
      config,
      quantityDisplay: buildQuantityDisplay(descriptor, config),
      selectedTreeNode: descriptor.tree_nodes[0]?.id ?? null,
      activeChartTab: descriptor.default_charts[0]?.id ?? 'overview',
      runId: null,
      runStatus: null,
      runResult: null,
      liveProbes: [],
      liveDecisions: [],
      logs: [],
      isRunning: false,
    });
  },

  setConfigValue: (name, value) => {
    set((s) => ({ config: setNested(s.config, name, value) }));
  },

  setConfig: (config) => set((s) => ({
    config,
    quantityDisplay: s.currentDescriptor
      ? buildQuantityDisplay(s.currentDescriptor, config)
      : {},
  })),

  setQuantityDisplay: (name, text) =>
    set((s) => ({ quantityDisplay: { ...s.quantityDisplay, [name]: text } })),

  setSelectedTreeNode: (nodeId) => set({ selectedTreeNode: nodeId }),

  setActiveChartTab: (tabId) => set({ activeChartTab: tabId }),

  setAgentBackend: (backend) => set({ agentBackend: backend }),

  setRunResult: (result) => set({ runResult: result }),

  appendLog: (msg) => set((s) => ({ logs: [...s.logs, msg] })),

  updateFromStream: (partial) => {
    set((s) => ({
      runResult: s.runResult ? { ...s.runResult, ...partial } : (partial as UnifiedRunResult),
      liveProbes: partial.probes ?? s.liveProbes,
      liveDecisions: partial.decisions ?? s.liveDecisions,
    }));
  },

  startRun: async () => {
    const { currentModelId, config, agentBackend } = get();
    if (!currentModelId) return;

    if (unsubscribeStream) {
      unsubscribeStream();
      unsubscribeStream = null;
    }

    const api = createSimApi(get().apiMode);
    set({
      isRunning: true,
      runStatus: 'running',
      runResult: null,
      liveProbes: [],
      liveDecisions: [],
      logs: [t('log.starting', { modelId: currentModelId })],
    });

    try {
      const mergedConfig: Record<string, unknown> = {
        ...config,
        agent: { ...(config.agent as Record<string, unknown> ?? {}), backend: agentBackend },
      };
      const iteration = mergedConfig.iteration as Record<string, unknown> | undefined;
      const created = await api.createRun({
        model_id: currentModelId,
        config: mergedConfig,
        agent: agentBackend,
        max_trials: (iteration?.max_trials as number) ?? 1,
      });

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
                    model_id: currentModelId,
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
              reason: decision.reason,
            }),
          );
        },
        onComplete: (result) => {
          set((s) => ({
            runResult: result,
            runStatus: result.status,
            isRunning: false,
            caseHistory: [...s.caseHistory, result].slice(-20),
          }));
          get().appendLog(t('log.complete'));
        },
        onError: (error) => {
          set({ isRunning: false, runStatus: 'failed' });
          get().appendLog(t('log.error', { error }));
        },
      });
    } catch (err) {
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
