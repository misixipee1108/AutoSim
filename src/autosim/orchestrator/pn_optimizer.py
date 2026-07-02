"""Parameter optimization orchestration for PN junction simulations."""

from __future__ import annotations

import itertools
import random
from typing import Any

from autosim.orchestrator.pn_runner import run_pn_trial
from autosim.pn.schemas import (
    PnDesignVarSpec,
    PnObjectiveSpec,
    PnOptimizationSpec,
    PnSimInput,
    PnTrialResult,
)


def _parse_constraint(constraint: str | None) -> tuple[str, float] | None:
    if not constraint:
        return None
    text = constraint.strip()
    for op in ("<=", ">=", "<", ">"):
        if op in text:
            _, val = text.split(op, 1)
            num = val.strip().split()[0]
            return op, float(num)
    return None


def _metric_value(result: PnTrialResult, name: str) -> float | None:
    mapping = {
        "Emax": result.Emax_numeric,
        "W": result.W_numeric,
        "W_psi": result.W_psi_numeric,
        "W_rho": result.W_rho_numeric,
        "Vbi": result.Vbi_numeric,
        "Cj": result.Cj_estimate,
        "newton_iterations": float(result.newton_iterations),
    }
    return mapping.get(name)


def _objective_score(result: PnTrialResult, obj: PnObjectiveSpec) -> float:
    value = _metric_value(result, obj.name)
    if value is None:
        return float("inf")

    parsed = _parse_constraint(obj.constraint)
    if parsed:
        op, limit = parsed
        if op in ("<", "<=") and value > limit:
            return float("inf")
        if op in (">", ">=") and value < limit:
            return float("inf")

    if obj.target == "min":
        return value
    if obj.target == "max":
        return -value
    if obj.target == "range":
        lo = obj.min if obj.min is not None else float("-inf")
        hi = obj.max if obj.max is not None else float("inf")
        if lo <= value <= hi:
            return 0.0
        return min(abs(value - lo), abs(value - hi))
    return value


def _trial_score(result: PnTrialResult, objectives: list[PnObjectiveSpec]) -> float:
    if not result.converged:
        return float("inf")
    return sum(_objective_score(result, obj) for obj in objectives)


def pareto_best(results: list[PnTrialResult], objectives: list[PnObjectiveSpec]) -> list[PnTrialResult]:
    """Non-dominated trials for multi-objective summary."""
    if not results or not objectives:
        return results

    def dominates(a: PnTrialResult, b: PnTrialResult) -> bool:
        scores_a = [_objective_score(a, o) for o in objectives]
        scores_b = [_objective_score(b, o) for o in objectives]
        if any(sa == float("inf") for sa in scores_a):
            return False
        if any(sb == float("inf") for sb in scores_b):
            return True
        return all(sa <= sb for sa, sb in zip(scores_a, scores_b)) and any(
            sa < sb for sa, sb in zip(scores_a, scores_b)
        )

    front: list[PnTrialResult] = []
    for r in results:
        if any(dominates(other, r) for other in results if other is not r):
            continue
        front.append(r)
    return front


def _sample_params(
    design_vars: list[PnDesignVarSpec],
    rng: random.Random,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for var in design_vars:
        if var.type == "integer":
            params[var.name] = rng.randint(int(var.min), int(var.max))
        else:
            params[var.name] = rng.uniform(var.min, var.max)
    return params


def _grid_params(design_vars: list[PnDesignVarSpec], max_points: int) -> list[dict[str, Any]]:
    if not design_vars:
        return [{}]
    per_var = max(2, int(max_points ** (1.0 / len(design_vars))))
    axes: list[list[Any]] = []
    for var in design_vars:
        if var.type == "integer":
            lo, hi = int(var.min), int(var.max)
            step = max(1, (hi - lo) // (per_var - 1)) if hi > lo else 1
            vals = list(range(lo, hi + 1, step))[:per_var]
        else:
            vals = [
                var.min + (var.max - var.min) * i / max(per_var - 1, 1)
                for i in range(per_var)
            ]
        axes.append(vals)
    combos = list(itertools.product(*axes))
    if len(combos) > max_points:
        combos = combos[:max_points]
    return [
        {design_vars[i].name: combo[i] for i in range(len(design_vars))}
        for combo in combos
    ]


def run_pn_optimization(base_input: PnSimInput) -> tuple[list[PnTrialResult], PnTrialResult | None]:
    """Run random, grid, or Optuna search over design variables."""
    spec = base_input.optimization
    if not spec.enabled or not spec.design_vars:
        result = run_pn_trial(base_input)
        return [result], result

    if spec.method == "optuna":
        return _run_optuna_optimization(base_input, spec)
    if spec.method == "genetic":
        return _run_genetic_optimization(base_input, spec)

    rng = random.Random(42)
    param_sets: list[dict[str, Any]]
    if spec.method == "grid":
        param_sets = _grid_params(spec.design_vars, spec.max_trials)
    else:
        param_sets = [_sample_params(spec.design_vars, rng) for _ in range(spec.max_trials)]

    results: list[PnTrialResult] = []
    best: PnTrialResult | None = None
    best_score = float("inf")

    for idx, params in enumerate(param_sets):
        trial_input = base_input.model_copy_with_params(params)
        trial_input.bias_scan.enabled = False
        result = run_pn_trial(trial_input, trial_index=idx)
        results.append(result)
        score = _trial_score(result, spec.objectives)
        if score < best_score:
            best_score = score
            best = result

    return results, best


def _run_optuna_optimization(
    base_input: PnSimInput,
    spec: PnOptimizationSpec,
) -> tuple[list[PnTrialResult], PnTrialResult | None]:
    try:
        import optuna
    except ImportError as exc:
        raise ImportError("Optuna required: pip install optuna") from exc

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    results: list[PnTrialResult] = []
    best: PnTrialResult | None = None
    best_score = float("inf")

    def objective(trial: optuna.Trial) -> float:
        nonlocal best, best_score
        params: dict[str, Any] = {}
        for var in spec.design_vars:
            if var.type == "integer":
                params[var.name] = trial.suggest_int(var.name, int(var.min), int(var.max))
            else:
                params[var.name] = trial.suggest_float(var.name, var.min, var.max)
        trial_input = base_input.model_copy_with_params(params)
        trial_input.bias_scan.enabled = False
        result = run_pn_trial(trial_input, trial_index=len(results))
        results.append(result)
        score = _trial_score(result, spec.objectives)
        if score < best_score:
            best_score = score
            best = result
        return score

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=spec.max_trials)
    return results, best


def _run_genetic_optimization(
    base_input: PnSimInput,
    spec: PnOptimizationSpec,
) -> tuple[list[PnTrialResult], PnTrialResult | None]:
    """Simple genetic algorithm over design variables."""
    if not spec.design_vars:
        result = run_pn_trial(base_input)
        return [result], result

    rng = random.Random(42)
    pop_size = max(4, min(spec.max_trials // 2, 20))
    generations = max(1, spec.max_trials // pop_size)
    population = [_sample_params(spec.design_vars, rng) for _ in range(pop_size)]
    results: list[PnTrialResult] = []
    best: PnTrialResult | None = None
    best_score = float("inf")

    def evaluate(params: dict[str, Any]) -> tuple[PnTrialResult, float]:
        nonlocal best, best_score
        trial_input = base_input.model_copy_with_params(params)
        trial_input.bias_scan.enabled = False
        result = run_pn_trial(trial_input, trial_index=len(results))
        results.append(result)
        score = _trial_score(result, spec.objectives)
        if score < best_score:
            best_score = score
            best = result
        return result, score

    scored = [(p, evaluate(p)[1]) for p in population]
    for _ in range(generations):
        scored.sort(key=lambda x: x[1])
        survivors = [p for p, _ in scored[: max(2, pop_size // 2)]]
        next_pop: list[dict[str, Any]] = list(survivors)
        while len(next_pop) < pop_size:
            a, b = rng.sample(survivors, 2)
            child = dict(a)
            for var in spec.design_vars:
                if rng.random() < 0.5:
                    child[var.name] = b[var.name]
                if rng.random() < 0.2:
                    if var.type == "integer":
                        child[var.name] = rng.randint(int(var.min), int(var.max))
                    else:
                        child[var.name] = rng.uniform(var.min, var.max)
            next_pop.append(child)
        scored = [(p, evaluate(p)[1]) for p in next_pop]

    return results, best
