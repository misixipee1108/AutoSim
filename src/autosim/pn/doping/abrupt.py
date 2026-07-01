"""Abrupt (step) PN junction doping profile."""

from __future__ import annotations


class AbruptJunctionDoping:
    name = "abrupt"

    def __init__(self, Na: float, Nd: float) -> None:
        self.Na = Na
        self.Nd = Nd

    def net_doping(self, x: float) -> float:
        if x < 0:
            return -self.Na
        return self.Nd

    def Na_at(self, x: float) -> float:
        return self.Na if x < 0 else 0.0

    def Nd_at(self, x: float) -> float:
        return 0.0 if x < 0 else self.Nd
