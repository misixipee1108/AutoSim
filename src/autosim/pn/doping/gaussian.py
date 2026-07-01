"""Gaussian diffusion-type doping profile."""

from __future__ import annotations

import math


class GaussianDoping:
    """Gaussian donor/acceptor distributions centered at the junction."""

    name = "gaussian"

    def __init__(
        self,
        Na: float,
        Nd: float,
        sigma: float = 1e-5,
    ) -> None:
        self.Na = Na
        self.Nd = Nd
        self.sigma = max(sigma, 1e-8)

    def net_doping(self, x: float) -> float:
        if x < 0:
            na = self.Na * math.exp(-(x**2) / (2.0 * self.sigma**2))
            return -na
        nd = self.Nd * math.exp(-(x**2) / (2.0 * self.sigma**2))
        return nd

    def Na_at(self, x: float) -> float:
        if x >= 0:
            return 0.0
        return self.Na * math.exp(-(x**2) / (2.0 * self.sigma**2))

    def Nd_at(self, x: float) -> float:
        if x < 0:
            return 0.0
        return self.Nd * math.exp(-(x**2) / (2.0 * self.sigma**2))

    @property
    def bulk_Na(self) -> float:
        return self.Na

    @property
    def bulk_Nd(self) -> float:
        return self.Nd
