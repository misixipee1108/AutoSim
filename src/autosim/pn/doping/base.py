"""Doping profile protocol."""

from __future__ import annotations

from typing import Protocol


class DopingProfile(Protocol):
    name: str

    def net_doping(self, x: float) -> float:
        """Net doping C(x) = Nd - Na in cm^-3."""
        ...
