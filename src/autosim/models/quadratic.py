"""Quadratic drag: F = c2 * v * |v|."""

from __future__ import annotations

import math
from typing import Any


class QuadraticDragModel:
    name = "quadratic"

    def __init__(self, params: dict[str, Any]) -> None:
        if "c2" not in params:
            raise ValueError("quadratic drag requires 'c2' parameter")
        self.params = {"c2": float(params["c2"])}
        self.c2 = self.params["c2"]

    def drag_force(self, v: float) -> float:
        # Opposes velocity
        return -self.c2 * v * abs(v)

    def terminal_velocity(self, mass: float, gravity: float) -> float:
        return math.sqrt(mass * gravity / self.c2)
