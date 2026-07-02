"""Parameter perturbation robustness analysis for PN junction simulations."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from autosim.orchestrator.pn_runner import run_pn_trial
from autosim.pn.schemas import PnSimInput, PnTrialResult


@dataclass
class RobustnessSpec:
    enabled: bool = True
    n_samples: int = 10
    perturbation_frac: float = 0.1
    seed: int = 42
    parameters: list[str] = field(default_factory=lambda: ["Na", "Nd", "Vapp"])


@dataclass
class RobustnessResult:
    base_result: PnTrialResult
    samples: list[PnTrialResult] = field(default_factory=list)
    convergence_rate: float = 0.0
    metric_spread: dict[str, float] = field(default_factory=dict)
    failed_parameters: list[dict[str, Any]] = field(default_factory=list)


def _perturb_value(value: float, frac: float, rng: random.Random) -> float:
    delta = value * frac * rng.uniform(-1.0, 1.0)
    return max(value + delta, value * 0.01)


def run_pn_robustness(
    base_input: PnSimInput,
    spec: RobustnessSpec | None = None,
) -> RobustnessResult:
    """Run base case plus perturbed parameter samples; report stability metrics."""
    cfg = spec or RobustnessSpec()
    rng = random.Random(cfg.seed)
    base = run_pn_trial(base_input, trial_index=0)
    samples: list[PnTrialResult] = []
    failed: list[dict[str, Any]] = []

    for idx in range(cfg.n_samples):
        params: dict[str, Any] = {}
        for name in cfg.parameters:
            base_val = getattr(base_input, name, None)
            if base_val is None or not isinstance(base_val, (int, float)):
                continue
            params[name] = _perturb_value(float(base_val), cfg.perturbation_frac, rng)
        trial_input = base_input.model_copy_with_params(params)
        trial_input.bias_scan.enabled = False
        result = run_pn_trial(trial_input, trial_index=idx + 1)
        samples.append(result)
        if not result.converged:
            failed.append(params)

    converged_count = sum(1 for s in samples if s.converged)
    spread: dict[str, float] = {}
    for metric in ("Vbi_numeric", "W_numeric", "Emax_numeric"):
        vals = [getattr(s, metric) for s in samples if getattr(s, metric) is not None]
        if len(vals) >= 2:
            spread[metric] = float(max(vals) - min(vals))

    return RobustnessResult(
        base_result=base,
        samples=samples,
        convergence_rate=converged_count / max(len(samples), 1),
        metric_spread=spread,
        failed_parameters=failed,
    )
