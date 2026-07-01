"""Piecewise / tabulated doping profile."""

from __future__ import annotations

import bisect


class PiecewiseDoping:
    """Net doping from piecewise-linear segments or tabulated (x, C) points."""

    name = "piecewise"

    def __init__(self, points: list[tuple[float, float]]) -> None:
        if len(points) < 2:
            raise ValueError("piecewise doping requires at least 2 points")
        sorted_pts = sorted(points, key=lambda p: p[0])
        self._xs = [p[0] for p in sorted_pts]
        self._cs = [p[1] for p in sorted_pts]

    def net_doping(self, x: float) -> float:
        if x <= self._xs[0]:
            return self._cs[0]
        if x >= self._xs[-1]:
            return self._cs[-1]
        idx = bisect.bisect_right(self._xs, x) - 1
        x0, x1 = self._xs[idx], self._xs[idx + 1]
        c0, c1 = self._cs[idx], self._cs[idx + 1]
        if x1 == x0:
            return c0
        t = (x - x0) / (x1 - x0)
        return c0 + t * (c1 - c0)

    def Na_at(self, x: float) -> float:
        return max(-self.net_doping(x), 0.0)

    def Nd_at(self, x: float) -> float:
        return max(self.net_doping(x), 0.0)

    @property
    def bulk_Na(self) -> float:
        return max(-self._cs[0], 0.0)

    @property
    def bulk_Nd(self) -> float:
        return max(self._cs[-1], 0.0)
