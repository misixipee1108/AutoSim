"""Semiconductor 1D drift-diffusion physics plugin."""

from __future__ import annotations

from autosim.plugins.physics.semiconductor_1d_poisson.plugin import Semiconductor1DPoissonPlugin


class Semiconductor1DDdPlugin(Semiconductor1DPoissonPlugin):
    interface_id = "semiconductor_1d_dd"

    def get_descriptor(self):
        import json
        from pathlib import Path

        from autosim.project.schemas import PhysicsInterfaceDescriptor

        manifest = Path(__file__).resolve().parents[1] / "manifests" / "semiconductor_1d_dd.json"
        with open(manifest, encoding="utf-8") as f:
            data = json.load(f)
        return PhysicsInterfaceDescriptor.model_validate(data)
