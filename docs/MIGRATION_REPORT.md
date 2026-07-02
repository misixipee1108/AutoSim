# AutoSim Legacy → v2 Migration Report

**Date:** 2026-07-02  
**Status:** Complete — single v2 architecture as sole entry path

## Summary

All PN Junction and Falling Block capabilities now run through **SimulationProject v2**, **PhysicsInterfacePlugin**, **StudyRunner**, and **ProjectAdapter**. Legacy descriptors, dual API paths, and frontend `projectMode` have been removed.

## Feature Matrix

| Capability | Legacy path | v2 path | Status |
|------------|-------------|---------|--------|
| Poisson / depletion | `PnAdapter` + YAML | `semiconductor_1d_poisson` + `stationary` | OK |
| Drift-diffusion / I-V | YAML + bias_scan | `semiconductor_1d_dd` + `bias_sweep` | OK |
| C-V sweep | cv_scan in YAML | `cv_sweep` study | OK |
| Transient DD | transient_dd | `time_dependent` study | OK |
| Optimization | pn_optimizer | `optimization` study | OK |
| Multi-trial agent | iteration | `parameter_sweep` study | OK |
| Falling block | FallingBlockAdapter | `mechanics_0d_falling_body` | OK |
| Probes / SSE | adapter callbacks | ProjectAdapter | OK |
| CSV/JSON/plot CLI | PnRunRecorder | ProjectRunRecorder | OK |
| Benchmark suite | legacy YAML cases | unchanged runner (internal) | OK |

## Deleted Files

- `src/autosim/api/model_registry/pn_junction_1d.json`
- `src/autosim/api/model_registry/falling_block.json`
- `frontend/src/mocks/pn_descriptor.json`
- `frontend/src/mocks/falling_block_descriptor.json`
- `frontend/src/components/model/QuantityInput.tsx` (legacy config UI)

## Deprecated / Internal Only

| Module | Reason | Remove when |
|--------|--------|-------------|
| `api/adapters/pn.py`, `falling_block.py` | Engine delegation | Inlined into plugins/engine |
| `legacy_flat_to_project()` | YAML conversion | Benchmarks use project JSON only |
| `model_registry/registry.py` | Raises on use | Can delete after script cleanup |

## Examples

17 project files under `examples/projects/*_v2.json` generated from `config/demo_*.yaml`.

Built-in templates: `pn_stationary`, `falling_body`.

## Tests

**154 tests passing**, including:

- `tests/project/test_pn_stationary_v2.py`
- `tests/project/test_pn_studies_v2.py`
- `tests/project/test_falling_body_v2.py`
- `tests/api/test_legacy_removed.py`
- `tests/api/test_api.py` (v2 endpoints)

## Known Limits

- Benchmark runner still executes legacy YAML internally (not yet wrapped in ProjectAdapter)
- `parameter_schema.py` does not expose all Results tree nodes
- PN robustness CLI command removed (can be re-added as study type)

## Documentation

- [architecture_v2.md](architecture_v2.md)
- [plugin_development.md](plugin_development.md)
- [MIGRATION.md](MIGRATION.md)
- [LEGACY_INVENTORY.md](LEGACY_INVENTORY.md)
