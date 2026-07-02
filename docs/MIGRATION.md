# Migration Guide: Legacy → v2

## Removed

| Legacy | Replacement |
|--------|-------------|
| `GET /api/models` | `GET /api/project/templates` + `GET /api/plugins/physics` |
| `POST /api/runs { model_id, config }` | `POST /api/runs { project }` |
| `pn_junction_1d.json` descriptor | `semiconductor_1d_poisson` / `semiconductor_1d_dd` manifests |
| `falling_block.json` descriptor | `mechanics_0d_falling_body` manifest |
| CLI `--sim pn\|falling_block` | `autosim run --project …` or `--config` (YAML auto-converts) |
| Frontend model dropdown | Project template selector |

## YAML → Project

Convert any demo YAML:

```bash
autosim export-project -c config/demo_pn_si_bias_sweep.yaml -o examples/projects/my_case_v2.json
```

Or load YAML directly:

```bash
autosim run -c config/demo_pn_si_equilibrium.yaml
```

## Field Mapping (PN)

| Legacy YAML | Project path |
|-------------|--------------|
| `Na`, `Nd`, `doping` | `model.physics_interfaces.*.settings.doping` |
| `Nx`, junction refinement | `model.mesh` |
| `Vapp`, `bias_scan` | `studies.*.parameters` |
| `solver.*` | `studies.*.solver_sequence[0].settings` |
| `agent.*` | `studies.*.agent` |
| `model_type` | physics settings + study type inference |

## Study Type Inference

| Legacy flags | `study_type` |
|--------------|--------------|
| `optimization.enabled` | `optimization` |
| `bias_scan.enabled` | `bias_sweep` |
| `cv_scan.enabled` | `cv_sweep` |
| `transient_dd` / `transient.enabled` | `time_dependent` |
| `iteration.max_trials > 1` | `parameter_sweep` |
| else | `stationary` |

## Internal Shims (not public)

- `PnAdapter` / `FallingBlockAdapter` — called only from `plugins/engine/`
- `legacy_flat_to_project()` — YAML/benchmark conversion; remove when all CI uses project JSON
