import type {
  CreateRunRequest,
  CreateRunResponse,
  ModelDescriptor,
  RunStatus,
  SimApi,
  StreamHandlers,
  UnifiedProbe,
  UnifiedRunResult,
} from '../types';
import mockPnResult from '../mocks/pn_result.json';
import mockFbResult from '../mocks/falling_block_result.json';
import pnDescriptor from '../mocks/pn_descriptor.json';
import fbDescriptor from '../mocks/falling_block_descriptor.json';

const MOCK_DESCRIPTORS: Record<string, ModelDescriptor> = {
  pn_junction_1d: pnDescriptor as unknown as ModelDescriptor,
  falling_block: fbDescriptor as unknown as ModelDescriptor,
};

const MOCK_RESULTS: Record<string, UnifiedRunResult> = {
  pn_junction_1d: mockPnResult as unknown as UnifiedRunResult,
  falling_block: mockFbResult as unknown as UnifiedRunResult,
};

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export class MockSimApi implements SimApi {
  private runs = new Map<string, UnifiedRunResult>();

  async listModels(): Promise<ModelDescriptor[]> {
    await delay(100);
    return Object.values(MOCK_DESCRIPTORS);
  }

  async getModel(modelId: string): Promise<ModelDescriptor> {
    await delay(50);
    const m = MOCK_DESCRIPTORS[modelId];
    if (!m) throw new Error(`Unknown model: ${modelId}`);
    return m;
  }

  async createRun(request: CreateRunRequest): Promise<CreateRunResponse> {
    const runId = `mock-${Date.now().toString(36)}`;
    const base = MOCK_RESULTS[request.model_id];
    if (!base) throw new Error(`No mock for ${request.model_id}`);

    const running: UnifiedRunResult = {
      ...base,
      run_id: runId,
      status: 'running',
      logs: [`[mock] Starting ${request.model_id}...`],
      probes: [],
      decisions: [],
      convergence: base.convergence.map((c) => ({ ...c, x: [], y: [] })),
      sweep: base.sweep ?? [],
    };
    this.runs.set(runId, running);

    return { run_id: runId, model_id: request.model_id, status: 'running' };
  }

  async getRun(runId: string): Promise<UnifiedRunResult> {
    const run = this.runs.get(runId);
    if (!run) throw new Error(`Run not found: ${runId}`);
    return run;
  }

  subscribeRun(runId: string, handlers: StreamHandlers): () => void {
    const run = this.runs.get(runId);
    if (!run) return () => {};

    const base = MOCK_RESULTS[run.model_id];
    let cancelled = false;

    (async () => {
      handlers.onStatus?.('running');
      handlers.onLog?.(`[mock] Simulating ${run.model_id}...`);

      const probeSteps = Math.max(...base.convergence.map((c) => c.x.length), 0);
      for (let i = 0; i < probeSteps; i++) {
        if (cancelled) return;
        await delay(200);
        const iter = base.convergence[0]?.x[i] ?? i;
        const convByProbe: Record<string, string> = {
          residual_norm: 'residual',
          scaled_residual_norm: 'scaled_residual',
          scaled_delta_norm: 'scaled_delta',
        };
        const probeDefs = base.probes.length > 0 ? base.probes : [{ name: 'residual_norm', label: 'Residual Norm', type: 'scalar' as const }];
        for (const def of probeDefs) {
          const convName = convByProbe[def.name];
          const convSeries = convName ? base.convergence.find((c) => c.name === convName) : undefined;
          const value = convSeries?.y[i] ?? 0;
          const probe: UnifiedProbe = {
            name: def.name,
            label: def.label,
            type: def.type as UnifiedProbe['type'],
            value: def.type === 'boolean' ? false : value,
            x: convSeries ? [iter] : undefined,
            y: convSeries ? [value] : undefined,
          };
          handlers.onProbe?.(probe);
        }
        if (run) {
          run.convergence = base.convergence.map((c) => ({
            ...c,
            x: c.x.slice(0, i + 1),
            y: c.y.slice(0, i + 1),
          }));
        }
      }

      if (cancelled) return;
      await delay(300);

      const final: UnifiedRunResult = {
        ...base,
        run_id: runId,
        status: 'completed',
        logs: [...(run.logs ?? []), '[mock] Run completed'],
      };
      this.runs.set(runId, final);

      if (base.decisions.length > 0) {
        handlers.onDecision?.(base.decisions[0]);
      }
      handlers.onStatus?.('completed');
      handlers.onComplete?.(final);
    })();

    return () => {
      cancelled = true;
    };
  }
}

export class LiveSimApi implements SimApi {
  private baseUrl = '';

  async listModels(): Promise<ModelDescriptor[]> {
    const r = await fetch(`${this.baseUrl}/api/models`);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async getModel(modelId: string): Promise<ModelDescriptor> {
    const r = await fetch(`${this.baseUrl}/api/models/${modelId}`);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async createRun(request: CreateRunRequest): Promise<CreateRunResponse> {
    const r = await fetch(`${this.baseUrl}/api/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async getRun(runId: string): Promise<UnifiedRunResult> {
    const r = await fetch(`${this.baseUrl}/api/runs/${runId}`);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  subscribeRun(runId: string, handlers: StreamHandlers): () => void {
    const es = new EventSource(`${this.baseUrl}/api/runs/${runId}/stream`);

    es.addEventListener('probe', (e) => {
      handlers.onProbe?.(JSON.parse(e.data));
    });
    es.addEventListener('decision', (e) => {
      handlers.onDecision?.(JSON.parse(e.data));
    });
    es.addEventListener('log', (e) => {
      const data = JSON.parse(e.data);
      handlers.onLog?.(data.message);
    });
    es.addEventListener('status', (e) => {
      const data = JSON.parse(e.data);
      handlers.onStatus?.(data.status as RunStatus);
    });
    es.addEventListener('complete', (e) => {
      handlers.onComplete?.(JSON.parse(e.data));
      es.close();
    });
    es.addEventListener('error', (e) => {
      if (e instanceof MessageEvent && e.data) {
        const data = JSON.parse(e.data);
        handlers.onError?.(data.error);
      }
      es.close();
    });

    return () => es.close();
  }
}

export function createSimApi(mode?: 'mock' | 'live'): SimApi {
  const m = mode ?? (import.meta.env.VITE_API_MODE as string) ?? 'mock';
  return m === 'live' ? new LiveSimApi() : new MockSimApi();
}
