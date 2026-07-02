"""Record SimulationProject v2 runs to CSV/JSON/plots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from autosim.api.adapters.falling_block import FallingBlockAdapter
from autosim.api.adapters.pn import PnAdapter
from autosim.api.adapters.project import ProjectAdapter
from autosim.project.schemas import SimulationProject
from autosim.recorder.logger import RunRecorder
from autosim.recorder.plots import generate_all_plots
from autosim.recorder.pn_logger import PnRunRecorder
from autosim.recorder.pn_plots import generate_pn_plots, plot_sweep_curves
from autosim.schemas import TrialResult


class ProjectRunRecorder:
    """Write run artifacts for a v2 project execution."""

    def __init__(self, output_dir: str | Path = "runs") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        project: SimulationProject,
        raw: Any,
        *,
        run_id: str = "cli",
    ) -> Path:
        adapter = ProjectAdapter()
        category = adapter._physics_category(project)
        if category == "mechanics":
            fb = FallingBlockAdapter()
            if isinstance(raw, list):
                recorder = RunRecorder(self.output_dir)
                for r in raw:
                    recorder.save_trial(r)
                generate_all_plots(raw, recorder.plots_dir)
                return recorder.run_dir
            recorder = RunRecorder(self.output_dir)
            recorder.save_trial(raw)
            generate_all_plots([raw], recorder.plots_dir)
            return recorder.run_dir

        pn = PnAdapter()
        recorder = PnRunRecorder(self.output_dir)
        if isinstance(raw, list):
            for r in raw:
                recorder.save_trial(r)
            generate_pn_plots(raw, recorder.plots_dir)
            last = raw[-1]
            if last.sweep and last.sweep.points:
                plot_sweep_curves(last.sweep, recorder.plots_dir / "sweep_curves.png")
            recorder.save_validation_report(raw)
            recorder.save_summary(raw)
            return recorder.run_dir

        recorder.save_trial(raw)
        generate_pn_plots([raw], recorder.plots_dir)
        if getattr(raw, "sweep", None) and raw.sweep.points:
            plot_sweep_curves(raw.sweep, recorder.plots_dir / "sweep_curves.png")
        recorder.save_validation_report([raw])
        unified = adapter.normalize_result(run_id, project, raw)
        _ = unified
        return recorder.run_dir
