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
