"""Linear drag: F = c1 * v."""

from __future__ import annotations

from typing import Any


class LinearDragModel:
    name = "linear"

    def __init__(self, params: dict[str, Any]) -> None:
        if "c1" not in params:
            raise ValueError("linear drag requires 'c1' parameter")
        self.params = {"c1": float(params["c1"])}
        self.c1 = self.params["c1"]

    def drag_force(self, v: float) -> float:
        # Opposes velocity (Stokes drag)
        return -self.c1 * v

    def terminal_velocity(self, mass: float, gravity: float) -> float | None:
        if self.c1 == 0:
            return None
        return mass * gravity / self.c1
