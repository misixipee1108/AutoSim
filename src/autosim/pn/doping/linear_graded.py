"""Linear graded junction doping profile."""

from __future__ import annotations


class LinearGradedDoping:
    """Linear transition of net doping across the junction region."""

    name = "linear_graded"

    def __init__(
        self,
        Na: float,
        Nd: float,
        width: float = 1e-5,
    ) -> None:
        self.Na = Na
        self.Nd = Nd
        self.width = max(width, 1e-8)

    def net_doping(self, x: float) -> float:
        half = self.width / 2.0
        if x <= -half:
            return -self.Na
        if x >= half:
            return self.Nd
        # Linear blend from -Na at x=-half to +Nd at x=+half
        t = (x + half) / self.width
        return -self.Na + t * (self.Na + self.Nd)

    def Na_at(self, x: float) -> float:
        return max(-self.net_doping(x), 0.0) if x < 0 else 0.0

    def Nd_at(self, x: float) -> float:
        return max(self.net_doping(x), 0.0) if x >= 0 else 0.0

    @property
    def bulk_Na(self) -> float:
        return self.Na

    @property
    def bulk_Nd(self) -> float:
        return self.Nd
