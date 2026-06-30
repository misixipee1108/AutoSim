"""Polynomial drag: F = sum(c_i * v^i) for i >= 1."""

from __future__ import annotations

from typing import Any


class PolynomialDragModel:
    name = "polynomial"

    def __init__(self, params: dict[str, Any]) -> None:
        if "coeffs" not in params:
            raise ValueError("polynomial drag requires 'coeffs' list parameter")
        coeffs = [float(c) for c in params["coeffs"]]
        if not coeffs:
            raise ValueError("coeffs must be non-empty")
        self.params = {"coeffs": coeffs}
        self.coeffs = coeffs

    def drag_force(self, v: float) -> float:
        if v == 0:
            return 0.0
        magnitude = 0.0
        abs_v = abs(v)
        for i, c in enumerate(self.coeffs, start=1):
            magnitude += c * (abs_v**i)
        import math
        return -math.copysign(magnitude, v)

    def term_contributions(self, v: float) -> list[float]:
        abs_v = abs(v)
        return [c * (abs_v**i) for i, c in enumerate(self.coeffs, start=1)]

    def dominant_term_index(self, v: float) -> int:
        contribs = self.term_contributions(v)
        if not contribs:
            return 0
        return max(range(len(contribs)), key=lambda i: abs(contribs[i]))
