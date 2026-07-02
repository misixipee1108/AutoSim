import type {
  BenchmarkReport,
  BenchmarkReportListItem,
  BenchmarkRunResponse,
  CreateRunRequest,
  CreateRunResponse,
  ModelTreeSchema,
  ProjectTemplateListItem,
  RunStatus,
  SimApi,
  SimulationProject,
  StreamHandlers,
  UnifiedProbe,
  UnifiedRunResult,
} from '../types';
import mockPnResult from '../mocks/pn_result.json';
import mockFbResult from '../mocks/falling_block_result.json';
import mockPnProject from '../mocks/pn_project_v2.json';
import mockFbProject from '../mocks/fb_project_v2.json';
import { buildMockProjectTree } from '../mocks/projectTree';
import { resolveProjectParameters } from '../utils/projectParameters';
import mockBenchmarkReport from '../mocks/benchmark_report.json';
import mockBenchmarkMarkdown from '../mocks/benchmark_report.md?raw';

const MOCK_PN_PROJECT = mockPnProject as unknown as SimulationProject;
const MOCK_FB_PROJECT = mockFbProject as unknown as SimulationProject;

export const FALLBACK_PROJECT_TEMPLATES: ProjectTemplateListItem[] = [
  {
    template_id: 'pn_stationary',
    project_id: MOCK_PN_PROJECT.project_id,
    title: MOCK_PN_PROJECT.title,
    active_study_id: MOCK_PN_PROJECT.active_study_id,
  },
  {
    template_id: 'falling_body',
    project_id: MOCK_FB_PROJECT.project_id,
    title: MOCK_FB_PROJECT.title,
    active_study_id: MOCK_FB_PROJECT.active_study_id,
  },
];

const MOCK_RESULTS: Record<string, UnifiedRunResult> = {
  pn_si_equilibrium_demo: mockPnResult as unknown as UnifiedRunResult,
  falling_body_v2: mockFbResult as unknown as UnifiedRunResult,
};

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export function getMockProjectTemplate(templateId: string): SimulationProject {
  if (templateId === 'falling_body') {
    return structuredClone(MOCK_FB_PROJECT);
  }
  return structuredClone(MOCK_PN_PROJECT);
}

export class MockSimApi implements SimApi {
  private runs = new Map<string, UnifiedRunResult>();

  async listProjectTemplates(): Promise<ProjectTemplateListItem[]> {
    await delay(50);
    return FALLBACK_PROJECT_TEMPLATES;
  }

  async getProjectTemplate(templateId: string): Promise<SimulationProject> {
    await delay(50);
    return getMockProjectTemplate(templateId);
  }

  async getProjectTreeSchema(project?: SimulationProject): Promise<ModelTreeSchema> {
    await delay(30);
    return buildMockProjectTree(project ?? MOCK_PN_PROJECT);
  }

  async getProjectParameters(project: SimulationProject, treePath: string) {
    await delay(20);
    return { tree_path: treePath, parameters: resolveProjectParameters(project, treePath) };
  }

  async createRun(request: CreateRunRequest): Promise<CreateRunResponse> {
    const runId = `mock-${Date.now().toString(36)}`;
    const project = request.project as unknown as SimulationProject;
    const modelKey = project?.project_id ?? 'pn_si_equilibrium_demo';
    const base = MOCK_RESULTS[modelKey] ?? MOCK_RESULTS.pn_si_equilibrium_demo;
    if (!base) throw new Error(`No mock for ${modelKey}`);

    const running: UnifiedRunResult = {
      ...base,
      run_id: runId,
      status: 'running',
      logs: [`[mock] Starting ${modelKey}...`],
      probes: [],
      decisions: [],
      convergence: base.convergence.map((c) => ({ ...c, x: [], y: [] })),
      sweep: base.sweep ?? [],
    };
    this.runs.set(runId, running);

    return { run_id: runId, model_id: modelKey, status: 'running' };
  }

  async getRun(runId: string): Promise<UnifiedRunResult> {
    const run = this.runs.get(runId);
    if (!run) throw new Error(`Run not found: ${runId}`);
    return run;
  }

  subscribeRun(runId: string, handlers: StreamHandlers): () => void {
    const run = this.runs.get(runId);
    if (!run) return () => {};

    const base = MOCK_RESULTS[run.model_id] ?? MOCK_RESULTS.pn_si_equilibrium_demo;
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

  async listBenchmarkReports(): Promise<BenchmarkReportListItem[]> {
    await delay(80);
    return [
      {
        run_id: MOCK_BENCHMARK_REPORT.run_id,
        timestamp: MOCK_BENCHMARK_REPORT.timestamp,
        git_commit: MOCK_BENCHMARK_REPORT.git_commit,
        benchmark_suite: MOCK_BENCHMARK_REPORT.benchmark_suite,
        output_dir: MOCK_BENCHMARK_REPORT.output_dir,
        total: MOCK_BENCHMARK_REPORT.summary.total,
        passed_count: MOCK_BENCHMARK_REPORT.summary.passed_count,
        warning_count: MOCK_BENCHMARK_REPORT.summary.warning_count,
        failed_count: MOCK_BENCHMARK_REPORT.summary.failed_count,
        total_runtime_s: MOCK_BENCHMARK_REPORT.summary.total_runtime_s,
        overall_passed: MOCK_BENCHMARK_REPORT.summary.overall_passed,
      },
    ];
  }

  async getBenchmarkReport(runId: string): Promise<BenchmarkReport> {
    await delay(80);
    if (runId === MOCK_BENCHMARK_REPORT.run_id) {
      return MOCK_BENCHMARK_REPORT;
    }
    throw new Error(`Benchmark report not found: ${runId}`);
  }

  async getBenchmarkReportMarkdown(runId: string): Promise<string> {
    await delay(50);
    if (runId === MOCK_BENCHMARK_REPORT.run_id) {
      return mockBenchmarkMarkdown;
    }
    throw new Error(`Benchmark markdown not found: ${runId}`);
  }

  async runBenchmarkSuite(): Promise<BenchmarkRunResponse> {
    await delay(500);
    return {
      run_id: MOCK_BENCHMARK_REPORT.run_id,
      overall_passed: MOCK_BENCHMARK_REPORT.summary.overall_passed,
      total: MOCK_BENCHMARK_REPORT.summary.total,
      passed_count: MOCK_BENCHMARK_REPORT.summary.passed_count,
      warning_count: MOCK_BENCHMARK_REPORT.summary.warning_count,
      failed_count: MOCK_BENCHMARK_REPORT.summary.failed_count,
      total_runtime_s: MOCK_BENCHMARK_REPORT.summary.total_runtime_s,
      output_dir: MOCK_BENCHMARK_REPORT.output_dir,
    };
  }
}

const MOCK_BENCHMARK_REPORT = mockBenchmarkReport as unknown as BenchmarkReport;

const LIVE_FETCH_TIMEOUT_MS = 8000;
const LIVE_UI_FETCH_TIMEOUT_MS = 2000;
const LIVE_PROBE_TIMEOUT_MS = 2000;

async function liveFetch(url: string, init?: RequestInit, timeoutMs = LIVE_FETCH_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error(`Request timed out after ${timeoutMs}ms: ${url}`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export async function probeLiveApi(timeoutMs = LIVE_PROBE_TIMEOUT_MS): Promise<boolean> {
  try {
    const r = await liveFetch('/api/health', undefined, timeoutMs);
    return r.ok;
  } catch {
    return false;
  }
}

export class LiveSimApi implements SimApi {
  private baseUrl = '';

  async listProjectTemplates(): Promise<ProjectTemplateListItem[]> {
    const r = await liveFetch(`${this.baseUrl}/api/project/templates`, undefined, LIVE_UI_FETCH_TIMEOUT_MS);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async getProjectTemplate(templateId: string): Promise<SimulationProject> {
    const r = await liveFetch(
      `${this.baseUrl}/api/project/templates/${encodeURIComponent(templateId)}`,
      undefined,
      LIVE_UI_FETCH_TIMEOUT_MS,
    );
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async getProjectTreeSchema(project?: SimulationProject): Promise<ModelTreeSchema> {
    if (project) {
      const r = await liveFetch(
        `${this.baseUrl}/api/project/tree-schema`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(project),
        },
        LIVE_UI_FETCH_TIMEOUT_MS,
      );
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    }
    const r = await liveFetch(`${this.baseUrl}/api/project/tree-schema`, undefined, LIVE_UI_FETCH_TIMEOUT_MS);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async getProjectParameters(project: SimulationProject, treePath: string) {
    const r = await liveFetch(
      `${this.baseUrl}/api/project/parameters?tree_path=${encodeURIComponent(treePath)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(project),
      },
    );
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async createRun(request: CreateRunRequest): Promise<CreateRunResponse> {
    const r = await liveFetch(`${this.baseUrl}/api/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async getRun(runId: string): Promise<UnifiedRunResult> {
    const r = await liveFetch(`${this.baseUrl}/api/runs/${runId}`);
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

  async listBenchmarkReports(): Promise<BenchmarkReportListItem[]> {
    const r = await liveFetch(`${this.baseUrl}/api/benchmarks/reports`);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async getBenchmarkReport(runId: string): Promise<BenchmarkReport> {
    const r = await liveFetch(`${this.baseUrl}/api/benchmarks/reports/${encodeURIComponent(runId)}`);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async getBenchmarkReportMarkdown(runId: string): Promise<string> {
    const r = await liveFetch(`${this.baseUrl}/api/benchmarks/reports/${encodeURIComponent(runId)}/markdown`);
    if (!r.ok) throw new Error(await r.text());
    return r.text();
  }

  async runBenchmarkSuite(): Promise<BenchmarkRunResponse> {
    const r = await liveFetch(`${this.baseUrl}/api/benchmarks/run`, { method: 'POST' });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }
}

export function createSimApi(mode?: 'mock' | 'live'): SimApi {
  const m = mode ?? (import.meta.env.VITE_API_MODE as string) ?? 'mock';
  return m === 'live' ? new LiveSimApi() : new MockSimApi();
}
