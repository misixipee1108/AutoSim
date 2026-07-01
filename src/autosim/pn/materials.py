"""Literature-sourced semiconductor material parameters."""

from __future__ import annotations

import math

from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialSpec:
    """Material constants with traceable source metadata."""

    name: str
    temperature_k: float
    eps_r: float
    ni: float  # cm^-3
    q: float  # C
    kB: float  # J/K
    eps_0: float  # F/cm
    source: str
    Eg_eV: float = 1.12
    mu_n: float = 1350.0  # cm^2/(V·s)
    mu_p: float = 480.0
    Nc: float = 2.8e19  # cm^-3
    Nv: float = 1.04e19
    chi: float = 4.05  # eV

    @property
    def eps(self) -> float:
        return self.eps_r * self.eps_0

    @property
    def Vt(self) -> float:
        return self.kB * self.temperature_k / self.q


# CODATA/NIST 2018 recommended values (SI); eps_0 in F/cm for CGS semiconductor units
Q_ELEMENTARY = 1.602176634e-19  # C, NIST CODATA
K_BOLTZMANN = 1.380649e-23  # J/K, NIST CODATA
EPS_0_CGS = 8.8541878128e-14  # F/cm


def silicon_300k() -> MaterialSpec:
    """Silicon at 300 K.

    eps_r: Sze & Ng, Physics of Semiconductor Devices, 4th ed., Ch. 1
    ni: Green, J. Appl. Phys. 67, 2944 (1990); consistent with Sze Table 1-1 order
    q, kB, eps_0: NIST CODATA 2018
    """
    return silicon_at_T(300.0)


def silicon_at_T(temperature_k: float) -> MaterialSpec:
    """Silicon at arbitrary temperature.

    eps_r: Sze & Ng (2012) Ch. 1 (weakly T-dependent; constant 11.7 for demo range)
    ni(T): Green (1990) JAP 67, 2944 intrinsic carrier density model
    q, kB, eps_0: NIST CODATA 2018
    """
    t = temperature_k
    ni = (
        5.29e19 * (t / 300.0) ** 2.54
        * math.exp(-6726.0 / t)
        * (t / 300.0) ** 1.5
    )
    return MaterialSpec(
        name="Si",
        temperature_k=t,
        eps_r=11.7,
        ni=ni,
        q=Q_ELEMENTARY,
        kB=K_BOLTZMANN,
        eps_0=EPS_0_CGS,
        source=(
            "Sze & Ng (2012) Physics of Semiconductor Devices 4th ed. Ch.1; "
            "Green (1990) JAP 67, 2944 ni(T); NIST CODATA 2018"
        ),
    )
