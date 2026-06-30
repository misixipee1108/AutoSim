"""Experiment data recording."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from autosim.schemas import TrialResult


class RunRecorder:
    def __init__(self, base_dir: str | Path = "runs") -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path(base_dir) / timestamp
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "plots").mkdir(exist_ok=True)

    def save_trial(self, result: TrialResult) -> None:
        trial_dir = self.run_dir / f"trial_{result.trial_index:03d}"
        trial_dir.mkdir(exist_ok=True)

        with open(trial_dir / "input.json", "w", encoding="utf-8") as f:
            json.dump(result.input.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

        metrics = {
            "trial_index": result.trial_index,
            "impact_time": result.impact_time,
            "impact_velocity": result.impact_velocity,
            "terminal_velocity_estimate": result.terminal_velocity_estimate,
            "early_stopped": result.early_stopped,
            "stop_reason": result.stop_reason,
            "num_probes": len(result.probes),
            "num_trajectory_points": len(result.trajectory),
        }
        with open(trial_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        with open(trial_dir / "probes.jsonl", "w", encoding="utf-8") as f:
            for probe in result.probes:
                f.write(probe.model_dump_json() + "\n")

        with open(trial_dir / "decisions.jsonl", "w", encoding="utf-8") as f:
            for decision in result.decisions:
                f.write(decision.model_dump_json() + "\n")

    def save_summary(self, results: list[TrialResult]) -> Path:
        summary_path = self.run_dir / "trials_summary.csv"
        fieldnames = [
            "trial_index",
            "drag_model",
            "drag_params",
            "impact_time",
            "impact_velocity",
            "terminal_velocity_estimate",
            "early_stopped",
            "stop_reason",
            "num_probes",
        ]
        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow(
                    {
                        "trial_index": r.trial_index,
                        "drag_model": r.input.drag_model.value,
                        "drag_params": json.dumps(r.input.drag_params),
                        "impact_time": r.impact_time,
                        "impact_velocity": r.impact_velocity,
                        "terminal_velocity_estimate": r.terminal_velocity_estimate,
                        "early_stopped": r.early_stopped,
                        "stop_reason": r.stop_reason,
                        "num_probes": len(r.probes),
                    }
                )
        return summary_path

    @property
    def plots_dir(self) -> Path:
        return self.run_dir / "plots"
