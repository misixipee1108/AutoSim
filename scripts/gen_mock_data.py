"""Generate frontend mock JSON files from real simulations."""

import json
from pathlib import Path

from autosim.api.adapters.falling_block import FallingBlockAdapter
from autosim.api.adapters.pn import PnAdapter
from autosim.api.model_registry.registry import get_model
from autosim.orchestrator.pn_runner import run_pn_trial, run_pn_with_sweep
from autosim.orchestrator.runner import run_trial
from autosim.pn.schemas import PnSimInput
from autosim.schemas import AgentBackend, AgentConfig, SimInput

out = Path("frontend/src/mocks")
out.mkdir(parents=True, exist_ok=True)

(out / "falling_block_descriptor.json").write_text(
    json.dumps(get_model("falling_block").model_dump(), indent=2), encoding="utf-8"
)
(out / "pn_descriptor.json").write_text(
    json.dumps(get_model("pn_junction_1d").model_dump(), indent=2), encoding="utf-8"
)

fb = FallingBlockAdapter()
sim = SimInput(
    mass=1.0,
    y0=50.0,
    t_max=8.0,
    probe_interval=0.2,
    dt=0.01,
    drag_params={"c2": 0.5},
    agent=AgentConfig(backend=AgentBackend.RULES),
)
fb_result = fb.normalize_result("mock-fb", run_trial(sim))
(out / "falling_block_result.json").write_text(
    json.dumps(fb_result.model_dump(), indent=2), encoding="utf-8"
)

pn = PnAdapter()
psim = PnSimInput(
    Na=1e18,
    Nd=1e16,
    Nx=120,
    tol=1e-3,
    max_iter=80,
    agent={"backend": AgentBackend.RULES},
    bias_scan={"enabled": True, "Vapp_list": [0.0, -0.3, 0.2]},
)
results, _ = run_pn_with_sweep(psim)
pn_result = pn.normalize_result("mock-pn", results[-1], all_trials=results)
(out / "pn_result.json").write_text(
    json.dumps(pn_result.model_dump(), indent=2), encoding="utf-8"
)
print("Mock files written to", out)
