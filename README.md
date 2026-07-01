# AutoSim

Agent-native physics simulation prototype: falling block with air drag, structured probes, and LLM-assisted monitoring.

## Features

- **Physics model:** 1D vertical free fall with configurable drag
- **Drag theories:** linear, quadratic, polynomial, custom expression
- **Probes:** common diagnostics + theory-specific probes emitted during simulation
- **Agent backends:** rules-only, DeepSeek API, or hybrid (LLM + rules veto)
- **Workflow:** COMSOL-style forward simulation with optional multi-trial iteration
- **Output:** JSON/JSONL logs, CSV summary, trajectory and convergence plots

## Installation

```bash
cd d:\AutoSim
pip install -e ".[dev]"
```

## Web Frontend (Demo Workbench)

Schema-driven React workbench for **Falling Block** and **1D PN Junction** with mock or live API modes.

### Backend API

```bash
uvicorn autosim.api.main:app --reload --port 8000
```

Endpoints: `GET /api/models`, `GET /api/models/{id}`, `POST /api/runs`, `GET /api/runs/{id}`, `GET /api/runs/{id}/stream` (SSE).

### Frontend

```bash
cd frontend
npm install
npm run dev          # mock mode (no backend required)
npm run dev:live     # live mode — proxies /api to localhost:8000
```

Toggle **Live API** in the toolbar to switch modes at runtime. Both models share a unified result protocol (`profiles`, `time_series`, `convergence`, `probes`, `decisions`).

Regenerate mock data from real simulations:

```bash
python scripts/gen_mock_data.py
```

## Configuration

Copy `.env.example` to `.env` and set your DeepSeek API key (optional for rules-only mode):

```
DEEPSEEK_API_KEY=your_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

## Quick Start

Single trial (rules agent, no API needed):

```bash
autosim run -c config/demo_falling_block.yaml --agent rules
```

Multi-trial iteration:

```bash
autosim iterate -c config/demo_falling_block.yaml --agent rules --max-trials 3
```

With DeepSeek:

```bash
autosim run -c config/demo_falling_block.yaml --agent hybrid
```

Output is written to `runs/<timestamp>/`.

## 1D PN Junction (Poisson)

Nonlinear 1D Poisson solver for abrupt Si PN junction with Newton iteration probes and depletion-approximation validation.

```bash
python -m autosim.cli run --sim pn -c config/demo_pn_si_equilibrium.yaml --agent rules
python -m autosim.cli iterate --sim pn -c config/demo_pn_si_equilibrium.yaml --agent rules --max-trials 2
```

### Physics & units

- Coordinate: `x=0` at junction; P-side `x<0`, N-side `x>0`
- Units: length (cm), doping (cm⁻³), potential (V), field (V/cm)
- Boltzmann carriers: `n = ni·exp(ψ/Vt)`, `p = ni·exp(-ψ/Vt)`
- Material defaults from literature (Si @ 300 K):

| Parameter | Value | Source |
|-----------|-------|--------|
| eps_r | 11.7 | Sze & Ng (2012) Ch. 1 |
| ni | 1.0×10¹⁰ cm⁻³ | Green (1990) JAP 67, 2944 |
| q, kB, eps_0 | CODATA | NIST |

### Validation

Numerical results are compared against depletion approximation (Sze Ch. 2):

- Vbi = Vt·ln(Na·Nd/ni²)
- W = sqrt(2ε/q · (1/Na + 1/Nd) · (Vbi - Vapp))

**Note:** Full Poisson with Boltzmann carriers differs from depletion approximation; W tolerance is relaxed (~40%) accordingly. This MVP does not claim TCAD-grade accuracy.

### PN config example

See [`config/demo_pn_si_equilibrium.yaml`](config/demo_pn_si_equilibrium.yaml) — includes `sources` field and `#` citation comments.

### PN probe fields

`iteration`, `residual_norm`, `scaled_residual_norm`, `scaled_delta_norm`, `residual_scale`, `solution_scale`, `relative_tol`, `residual_reduction_rate`, `delta_norm`, `damping_factor`, `jacobian_condition_estimate`, `max_psi`, `min_psi`, `max_electric_field`, `max_carrier_density`, `charge_neutrality_error`, `is_nan`, `is_unphysical`, `exp_clamped`, `stalled`, `convergence_status`

### PN convergence (COMSOL-style)

Newton convergence uses **scaled relative** criteria separate from analytic validation:

- **Criterion** (`solver.convergence.criterion`): `residual`, `solution`, `either`, or `both` (default: `both`)
- **Relative tolerance**: flat `tol` in YAML is an alias for `relative_tol`
- **Scaling**: `auto` uses initial residual norm and initial ψ scale; `manual` uses user `residual_scale` / `solution_scale`
- Converged when scaled residual **and** scaled Newton step (for `both`) are below `relative_tol`

Three status layers in results:

| Layer | Meaning |
|-------|---------|
| `solver_status` | Newton outcome only |
| `validation_status` | Abrupt-junction benchmark vs depletion analytic (not used for Newton stop) |
| `run_status` | Workflow summary (`completed`, `completed_with_warning`, `failed`, …) |

If Newton stops at `max_iter_reached` but validation passes, `run_status` is `completed_with_warning`.

### PN output

```
runs/pn_<timestamp>/
├── validation.json
├── trials_summary.csv
├── plots/
│   ├── psi_trial_000.png
│   ├── E_trial_000.png
│   ├── carriers_trial_000.png
│   └── newton_residual_trial_000.png
└── trial_000/
    ├── input.json, metrics.json, profile.json
    ├── probes.jsonl, decisions.jsonl
```

## Drag Models

| Model | Formula | Parameters |
|-------|---------|------------|
| `linear` | F = c1 · v | `c1` |
| `quadratic` | F = c2 · v · \|v\| | `c2` |
| `polynomial` | F = Σ cᵢ · vⁱ (i≥1) | `coeffs: [c1, c2, ...]` |
| `custom` | user expression | `expression`, plus named constants |

Custom expression example (use `abs_v` for speed magnitude, `v` for signed velocity):

```yaml
drag_model: custom
drag_params:
  expression: "c1 * abs_v + c2 * abs_v * abs_v"
  c1: 0.1
  c2: 0.05
```

Allowed variables: `v`, `abs_v`, plus named constants. Allowed functions: `abs`, `pow`, `sqrt`, `sin`, `cos`, `exp`, `log`.

## Probe Fields

**Common (all models):** `t`, `y`, `v`, `a`, `ke`, `pe`, `energy_drift`, `distance_to_ground`, `is_diverging`, `is_nan`, `drag_force`

**Theory-specific:**

- linear: `v_terminal_linear`, `drag_weight_ratio`
- quadratic: `v_terminal_quad`, `reynolds_like`, `drag_weight_ratio`
- polynomial: `dominant_term`, `term_fractions`, `term_contributions`
- custom: `drag_value`, `drag_sensitivity`

## Output Files

```
runs/<timestamp>/
├── trials_summary.csv
├── plots/
│   ├── trajectory_trial_000.png
│   └── convergence.png          # multi-trial only
└── trial_000/
    ├── input.json
    ├── metrics.json
    ├── probes.jsonl
    └── decisions.jsonl
```

## Agent Decisions

Structured actions: `continue`, `early_stop`, `adjust_search_space`, `explain_failure`, `recommend_next`.

In `iterate` mode, post-run `recommend_next` decisions with `suggested_params` drive the next trial.

## Testing

```bash
pytest
```

## Example Configs

| File | Drag model |
|------|------------|
| [`config/demo_falling_block.yaml`](config/demo_falling_block.yaml) | quadratic |
| [`config/demo_linear.yaml`](config/demo_linear.yaml) | linear |
| [`config/demo_polynomial.yaml`](config/demo_polynomial.yaml) | polynomial |
| [`config/demo_custom.yaml`](config/demo_custom.yaml) | custom |
| [`config/demo_pn_si_equilibrium.yaml`](config/demo_pn_si_equilibrium.yaml) | PN equilibrium |
| [`config/demo_pn_si_reverse_bias.yaml`](config/demo_pn_si_reverse_bias.yaml) | PN reverse bias |
| [`config/demo_pn_erfc.yaml`](config/demo_pn_erfc.yaml) | erfc diffused doping |
| [`config/demo_pn_iv.yaml`](config/demo_pn_iv.yaml) | DD Gummel I-V sweep |
| [`config/demo_pn_cv.yaml`](config/demo_pn_cv.yaml) | C-V differential capacitance |
| [`config/demo_pn_recombination.yaml`](config/demo_pn_recombination.yaml) | SRH recombination DD |
| [`config/demo_pn_pulse.yaml`](config/demo_pn_pulse.yaml) | Transient pulse bias |
| [`config/demo_pn_breakdown.yaml`](config/demo_pn_breakdown.yaml) | Breakdown / impact ionization |
