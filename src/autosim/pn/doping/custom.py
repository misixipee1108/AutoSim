"""Custom doping via safe expression in x."""

from __future__ import annotations

from typing import Any

from autosim.models.custom import evaluate_expression


class CustomDoping:
    name = "custom"

    def __init__(self, expression: str, params: dict[str, Any] | None = None) -> None:
        self.expression = expression
        self.params = {k: float(v) for k, v in (params or {}).items()}
        evaluate_expression(expression, {"x": 0.0, **self.params})

    def net_doping(self, x: float) -> float:
        return evaluate_expression(self.expression, {"x": float(x), **self.params})

    def net_doping_array(self, x) -> "object":
        import numpy as np

        xs = np.asarray(x, dtype=float)
        return np.array([self.net_doping(float(xi)) for xi in xs])
