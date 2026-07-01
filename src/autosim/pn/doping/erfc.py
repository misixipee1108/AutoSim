"""Complementary error-function (diffusion) doping profile."""

from __future__ import annotations

import math


class ErfcDoping:
    """Diffused junction: Nd and Na vary via erfc across xj (Sze Ch. 2 diffusion)."""

    name = "erfc"

    def __init__(self, Na: float, Nd: float, xj: float = 0.0, length: float = 1e-5) -> None:
        self.Na = Na
        self.Nd = Nd
        self.xj = xj
        self.length = max(length, 1e-12)

    def net_doping(self, x: float) -> float:
        from math import erfc

        u = (x - self.xj) / self.length
        nd = self.Nd * 0.5 * erfc(-u)
        na = self.Na * 0.5 * erfc(u)
        return nd - na

    def net_doping_array(self, x) -> "object":
        import numpy as np
        from scipy.special import erfc

        u = (np.asarray(x, dtype=float) - self.xj) / self.length
        nd = self.Nd * 0.5 * erfc(-u)
        na = self.Na * 0.5 * erfc(u)
        return nd - na
