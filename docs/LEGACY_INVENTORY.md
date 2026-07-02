# AutoSim Legacy → v2 Feature Inventory

Status key: **COVERED** | **MIGRATE** | **DELETE**

## Backend Entry & Registration

| Feature | Legacy Location | Status | v2 Target |
|---------|-----------------|--------|-----------|
| PN descriptor | `api/model_registry/pn_junction_1d.json` | DELETE | plugin manifest + project tree |
| FB descriptor | `api/model_registry/falling_block.json` | DELETE | `mechanics_0d_falling_body` manifest |
| `get_adapter()` | `api/model_registry/registry.py` | DELETE | `plugins/registry.py` |
| `PnAdapter` / `FallingBlockAdapter` | `api/adapters/pn.py`, `falling_block.py` | MIGRATE → internal | plugin engine only |
| `ProjectAdapter` | `api/adapters/project.py` | COVERED | sole public adapter |
| `POST /api/runs {model_id}` | `api/main.py` | DELETE | `{project}` only |
| `GET /api/models` | `api/main.py` | DELETE | `/api/project/templates` |
| CLI `--sim pn\|falling_block` | `cli.py` | DELETE | `--project` |
| Benchmark API | `api/benchmark_store.py` | MIGRATE | project conversion layer |

## PN Junction Capabilities

| Capability | Legacy | v2 Status |
|------------|--------|-----------|
| Poisson / depletion | `PnRunConfig.model_type` | COVERED via `semiconductor_1d_poisson` |
| Drift-diffusion | `drift_diffusion` | MIGRATE → `semiconductor_1d_dd` |
| Bias sweep | `bias_scan.enabled` | MIGRATE → `bias_sweep` study |
| I-V sweep | DD + bias | MIGRATE → `bias_sweep` + DD plugin |
| C-V sweep | `cv_scan` | MIGRATE → `cv_sweep` study |
| Transient | `transient_dd` | MIGRATE → `time_dependent` study |
| Breakdown / recombination | config fields | MIGRATE → physics settings |
| Validation | `pn/validation.py` | COVERED via result protocol |
| Probe / agent SSE | adapter callbacks | COVERED via ProjectAdapter |
| Case history / task queue | frontend store | COVERED generic metadata |
| CSV/JSON/plot | `recorder/` + CLI | MIGRATE → `ProjectRunRecorder` |
| Optimization | `pn_optimizer` | MIGRATE → `optimization` study |
| Multi-trial iteration | `pn_runner.run_pn_iteration` | MIGRATE → `parameter_sweep` study |

## Falling Block

| Capability | Legacy | v2 Target |
|------------|--------|-----------|
| Drag models | `RunConfig` | `mechanics_0d_falling_body` plugin |
| Time series | `TrialResult.trajectory` | `time_dependent` study |
| Agent / probes | `FallingBlockAdapter` | ProjectAdapter + plugin |
| Charts | frontend mocks | `results.visualizations` |

## Frontend

| Component | Status | Action |
|-----------|--------|--------|
| ModelTree + DynamicParameterForm | COVERED | extend parameter paths |
| `projectMode` dual path | DELETE | project-only store |
| TopToolbar model dropdown | DELETE | template selector |
| PN-hardcoded charts | MIGRATE | generic `visualizations` |
| Legacy mocks | DELETE | project mocks only |

## Demo Configs (`config/demo_*.yaml`)

All 16 YAML files map to `examples/projects/*_v2.json` via `project/yaml_converter.py`.

## Tests

| File | Action |
|------|--------|
| `tests/project/test_pn_*.py` | extend per study |
| `tests/api/test_legacy_removed.py` | assert 404/410 |
| `tests/api/test_api.py` | rewrite v2 |

## Short-Term Internal Shims (not public API)

| Module | Delete When |
|--------|-------------|
| `legacy_flat_to_project()` | all benchmarks use project JSON |
| Internal `PnAdapter` calls from plugins | engine inlined under `plugins/engine/` |
