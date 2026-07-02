# AutoSim

Agent-native physics simulation prototype. Structured **probes** expose solver internals each iteration so rules or LLM agents can monitor convergence, explain failures, and suggest next parameters—without replacing the numerical kernel.

The project explores a **gray-box** workflow: agents read residuals, damping, field peaks, and anomaly flags, then return structured decisions (`continue`, `early_stop`, `refine_mesh`, `recommend_next_parameters`, …).

| Model | Role |
|-------|------|
| **Falling Block** | Nonlinear 0D demo (drag models) with theory-specific probes |
| **1D PN Junction** | Semiconductor stack: Poisson → depletion → drift-diffusion → transient DD, with 16 validation benchmarks |

A schema-driven **React workbench** and **FastAPI** backend share a unified result protocol (`profiles`, `time_series`, `convergence`, `probes`, `decisions`).

> Research prototype, not industrial TCAD. Cite literature in config `sources` for reproducibility.

## Features

- **Structured probes** — Newton/Gummel diagnostics, physics scalars, failure flags
- **Agent backends** — `rules`, DeepSeek API, or `hybrid` (LLM + rules veto)
- **COMSOL-style designer** — SimulationProject v2: Model / Simulation / Results sections, plugin physics interfaces, study runners
- **1D PN stack** — four `model_type` tiers, five doping profiles, Si/Ge/GaAs library, bias/C-V sweeps, recombination, transient, optimization
- **Web workbench** — collapsible model tree, live parameter schemas from API, visualization catalog (per-profile tabs or merged charts), benchmark workspace, mock or live API

## Project Layout

```
AutoSim/
├── src/autosim/
│   ├── simulator/       # Falling block
│   ├── pn/              # 1D PN solvers, doping, validation, benchmarks
│   ├── project/         # SimulationProject v2 schemas, tree, templates
│   ├── plugins/         # Physics interfaces + study plugins
│   ├── materials/       # YAML material library
│   ├── agent/           # Rules + DeepSeek
│   ├── orchestrator/    # Sweeps, optimization, batch runs
│   └── api/             # FastAPI + adapters
├── frontend/            # React + TypeScript workbench
├── config/              # Demo YAML (legacy + PN)
├── examples/projects/   # v2 JSON templates
├── benchmarks/pn/       # PN regression cases
└── tests/
```

## Installation

Python ≥ 3.11:

```bash
pip install -e ".[dev]"
pip install -e ".[dev,optimize]"   # optional Optuna
```

Optional DeepSeek (rules-only mode works without it):

```
DEEPSEEK_API_KEY=your_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

## Quick Start

### CLI

```bash
autosim run --project examples/projects/pn_si_stationary_v2.json --agent rules
autosim run -c config/demo_pn_si_equilibrium.yaml --agent rules   # YAML auto-converts
autosim export-project -c config/demo_pn_iv.yaml -o examples/projects/my_iv_v2.json
autosim benchmark pn
autosim benchmark pn --case symmetric_equilibrium
```

Runs write to `runs/` (JSON, JSONL, plots).

### API + Frontend

```bash
uvicorn autosim.api.main:app --reload --port 8000

cd frontend && npm install
npm run dev          # mock mode
npm run dev:live     # proxy /api → :8000
```

Submit a run (wrap project JSON):

```bash
curl -X POST http://localhost:8000/api/runs -H "Content-Type: application/json" \
  -d '{"project": <project-json>, "agent": "rules"}'
```

Load built-in template: `GET /api/project/templates/pn_stationary`.

### Key API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | Health check |
| `GET /api/project/templates` | Template list |
| `POST /api/project/tree-schema` | Three-root model tree for a project |
| `POST /api/project/parameters?tree_path=...` | Parameter schemas for a tree node |
| `POST /api/runs` | Start simulation (`project` body required) |
| `GET /api/runs/{id}/stream` | SSE progress |
| `GET /api/benchmarks/reports` | Benchmark report list |
| `POST /api/benchmarks/run` | Run PN benchmark suite |

Legacy `{ model_id, config }` runs are removed; use `project` payloads. See [docs/MIGRATION.md](docs/MIGRATION.md) and [docs/architecture_v2.md](docs/architecture_v2.md).

## Web Workbench

Professional simulation layout: **model tree** + parameter panel, central charts, solver/agent side panels, task history.

**Model tree (v2):** three roots — **Model**, **Simulation**, **Results**. Under **Physics Interfaces**, nodes follow field → group hierarchy (e.g. *Semiconductor* → *Physics Model* / *Doping*), not solver names. Branches collapse with ▶ toggles; only the path to the current selection auto-expands.

**Parameters:** selecting a tree node loads schemas from `POST /api/project/parameters` (live) or local mirrors (mock). PN physics model dropdown includes all four `model_type` values; doping profile includes abrupt, linear graded, gaussian, erfc, and piecewise.

**Charts:** overview, profile tabs (ψ, E, carriers, ρ), combined multi-series view, Newton convergence, sweeps, transient, optimization scatter. Visualization options control which series appear and layout (separate tabs vs merged).

**Other:** YAML/JSON import-export, multi-run profile compare, benchmark report viewer, Live API toggle in toolbar.

Example project: [`examples/projects/pn_si_stationary_v2.json`](examples/projects/pn_si_stationary_v2.json).

Regenerate mock fixtures from real runs: `python scripts/gen_mock_data.py`.

## SimulationProject v2

COMSOL-inspired JSON schema:

| Section | Contents |
|---------|----------|
| **Model** | Geometry, domains, materials, physics interfaces, BC/IC, mesh |
| **Simulation** | Studies (`stationary`, bias/C-V sweep, transient, …) + solver sequence |
| **Results** | Output variables + visualization recipes |

PN mounts as plugins `semiconductor_1d_poisson` (equilibrium Poisson/depletion) or `semiconductor_1d_dd` (Gummel / transient). `ProjectAdapter` normalizes to `UnifiedRunResult` for the UI.

## 1D PN Junction

1D semiconductor solver with agent-readable probes. Junction at `x = 0`; P-side `x < 0`, N-side `x > 0`. Units: cm, cm⁻³, V, V/cm.

### Physics (`model_type`)

| Type | Description |
|------|-------------|
| `poisson` | Nonlinear Poisson + Boltzmann carriers (default) |
| `depletion` | Depletion approximation |
| `drift_diffusion` | Gummel Poisson + continuity; I-V / C-V |
| `transient_dd` | Time-dependent DD with pulse/step bias |

### Doping (`doping.type`)

`abrupt`, `linear_graded`, `gaussian`, `erfc`, `piecewise`. Junction position `xj`; optional junction mesh refinement.

### Solvers & materials

Newton variants: `newton`, `damped_newton`, `newton_line_search`. COMSOL-style scaled convergence (`solver.convergence.criterion`: `residual`, `solution`, `either`, `both`).

Materials in `src/autosim/materials/library/` (Si, Ge, GaAs) with temperature-dependent `ni` and literature refs (Sze & Ng; Green 1990 for Si).

### Extended PN capabilities

Bias/C-V sweeps with warm start and continuation, SRH/Auger/radiative recombination, transient waveforms, Chynoweth breakdown heuristic, Optuna/grid optimization, robustness sweeps, Shockley I-V validation benchmark.

### Validation & benchmarks

Analytic checks vs depletion theory (Vbi, W). Status layers: `solver_status`, `validation_status`, `run_status`.

```bash
autosim benchmark pn
```

Scans `benchmarks/pn/` (16 cases: equilibrium, graded/erfc doping, mesh convergence, Newton stability, I-V Shockley, C-V, recombination, transient, breakdown, …). Outputs `benchmark_report.json` + `.md` under `reports/benchmarks/<timestamp>/`. UI benchmark workspace consumes the same JSON.

Validation modes in each `reference.json`: `analytic_abrupt`, `numerical_only`, `validation_unavailable`.

## Falling Block

1D vertical fall with drag models: `linear`, `quadratic`, `polynomial`, `custom` (expression). Probes include energy drift, terminal velocity estimates, Reynolds-like scalars, and divergence flags. Used as the simpler agent-native demo before PN complexity.

## Agent System

| Backend | Behavior |
|---------|----------|
| `rules` | Threshold-based (stall, NaN, condition number) |
| `deepseek` | LLM via DeepSeek API |
| `hybrid` | LLM proposal + rules veto |

Agents never replace the solver. In iterate mode, `recommend_next_parameters` can drive the next trial.

## Configuration

**Preferred:** v2 JSON under `examples/projects/` or exported via `autosim export-project`.

**Legacy YAML** still runs (`config/demo_*.yaml`); CLI converts to v2 internally. PN blocks: `geometry`, `doping`, `bias_scan`, `mesh`, `solver`, `recombination`, `transient`, `cv_scan`, `breakdown`, `optimization`, `agent`.

Notable demos: `demo_pn_si_equilibrium.yaml`, `demo_pn_iv.yaml`, `demo_pn_cv.yaml`, `demo_pn_pulse.yaml`, `demo_pn_graded.yaml`, `demo_falling_block.yaml`.

## Testing

```bash
pytest
pytest tests/pn/test_benchmarks.py
pytest tests/api/
pytest tests/project/
```

## Related Docs

| Document | Contents |
|----------|----------|
| [docs/architecture_v2.md](docs/architecture_v2.md) | v2 architecture |
| [docs/MIGRATION.md](docs/MIGRATION.md) | API and schema migration |
| [docs/plugin_development.md](docs/plugin_development.md) | Adding physics plugins |
| [AutoSim OverallPlan.md](AutoSim%20OverallPlan.md) | Vision and roadmap |
| [AutoSim 1D PN node.md](AutoSim%201D%20PN%20node.md) | PN requirements and probes |

## License

See repository for license terms.
