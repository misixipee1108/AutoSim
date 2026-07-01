"""Material library loader."""

from __future__ import annotations

import math
from pathlib import Path

import yaml

from autosim.pn.materials import (
    EPS_0_CGS,
    K_BOLTZMANN,
    Q_ELEMENTARY,
    MaterialSpec,
    silicon_at_T,
)

_LIBRARY_DIR = Path(__file__).parent / "library"


def _ni_green1990(temperature_k: float, ref_T: float, ref_ni: float) -> float:
    t = temperature_k
    return (
        ref_ni
        * (t / ref_T) ** 2.54
        * math.exp(-6726.0 / t * (ref_T / 300.0))
        * (t / ref_T) ** 1.5
    )


def _load_yaml(name: str) -> dict:
    key = name.lower().replace(" ", "")
    if key in ("si", "silicon"):
        path = _LIBRARY_DIR / "silicon.yaml"
    elif key in ("ge", "germanium"):
        path = _LIBRARY_DIR / "germanium.yaml"
    else:
        path = _LIBRARY_DIR / f"{key}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Material not in library: {name}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get(key.split(".")[0], data.get(list(data.keys())[0]))


def load_material(name: str = "Si", temperature_k: float = 300.0) -> MaterialSpec:
    """Load material from YAML library with temperature-dependent ni."""
    key = name.lower()
    if key in ("si", "silicon") and temperature_k == 300.0:
        return silicon_at_T(300.0)

    try:
        entry = _load_yaml(name)
    except FileNotFoundError:
        if key in ("si", "silicon"):
            return silicon_at_T(temperature_k)
        raise

    ref_T = float(entry.get("ni_ref_T", 300.0))
    ref_ni = float(entry.get("ni_ref_value", 1e10))
    ni = _ni_green1990(temperature_k, ref_T, ref_ni)

    source = entry.get("source", entry.get("eps_r_source", ""))
    spec = MaterialSpec(
        name=entry.get("name", name),
        temperature_k=temperature_k,
        eps_r=float(entry.get("eps_r", 11.7)),
        ni=ni,
        q=Q_ELEMENTARY,
        kB=K_BOLTZMANN,
        eps_0=EPS_0_CGS,
        source=source,
        Eg_eV=float(entry.get("Eg_eV", 1.12)),
        mu_n=float(entry.get("mu_n_cm2_Vs", 1350.0)),
        mu_p=float(entry.get("mu_p_cm2_Vs", 480.0)),
        Nc=float(entry.get("Nc_cm3", 2.8e19)),
        Nv=float(entry.get("Nv_cm3", 1.04e19)),
        chi=float(entry.get("chi_eV", 4.05)),
    )
    return spec


def list_materials() -> list[str]:
    return [p.stem for p in _LIBRARY_DIR.glob("*.yaml")]
