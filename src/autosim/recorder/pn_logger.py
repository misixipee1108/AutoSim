"""PN junction experiment recording."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from autosim.pn.schemas import PnSweepResult, PnTrialResult
from autosim.pn.validation import validation_run_passed


class PnRunRecorder:
    def __init__(self, base_dir: str | Path = "runs") -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path(base_dir) / f"pn_{timestamp}"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "plots").mkdir(exist_ok=True)

    def save_trial(self, result: PnTrialResult) -> None:
        trial_dir = self.run_dir / f"trial_{result.trial_index:03d}"
        trial_dir.mkdir(exist_ok=True)

        with open(trial_dir / "input.json", "w", encoding="utf-8") as f:
            json.dump(result.input.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

        metrics = {
            "trial_index": result.trial_index,
            "Vbi_numeric": result.Vbi_numeric,
            "W_numeric": result.W_numeric,
            "W_psi_numeric": result.W_psi_numeric,
            "W_rho_numeric": result.W_rho_numeric,
            "Emax_numeric": result.Emax_numeric,
            "Cj_estimate": result.Cj_estimate,
            "Cj_method": result.Cj_method,
            "newton_iterations": result.newton_iterations,
            "converged": result.converged,
            "solver_status": result.solver_status.value if result.solver_status else None,
            "run_status": result.run_status,
            "early_stopped": result.early_stopped,
            "stop_reason": result.stop_reason,
            "num_probes": len(result.probes),
        }
        if result.validation:
            metrics["validation"] = result.validation.model_dump(mode="json")

        with open(trial_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        with open(trial_dir / "probes.jsonl", "w", encoding="utf-8") as f:
            for probe in result.probes:
                f.write(probe.model_dump_json() + "\n")

        with open(trial_dir / "decisions.jsonl", "w", encoding="utf-8") as f:
            for decision in result.decisions:
                f.write(decision.model_dump_json() + "\n")

        with open(trial_dir / "profile.json", "w", encoding="utf-8") as f:
            json.dump(
                [p.model_dump(mode="json") for p in result.profile],
                f,
                indent=2,
            )

    def save_validation_report(self, results: list[PnTrialResult]) -> Path:
        report_path = self.run_dir / "validation.json"
        report = {
            "trials": [
                {
                    "trial_index": r.trial_index,
                    "converged": r.converged,
                    "validation": r.validation.model_dump(mode="json") if r.validation else None,
                    "sources": r.input.sources,
                }
                for r in results
            ],
            "all_passed": all(
                validation_run_passed(r.validation) for r in results if r.validation
            ) if any(r.validation for r in results) else True,
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        return report_path

    def save_summary(self, results: list[PnTrialResult]) -> Path:
        summary_path = self.run_dir / "trials_summary.csv"
        fieldnames = [
            "trial_index", "Na", "Nd", "Nx", "Vapp",
            "Vbi_numeric", "W_numeric", "Emax_numeric",
            "newton_iterations", "converged", "validation_pass", "stop_reason",
        ]
        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow({
                    "trial_index": r.trial_index,
                    "Na": r.input.Na,
                    "Nd": r.input.Nd,
                    "Nx": r.input.Nx,
                    "Vapp": r.input.Vapp,
                    "Vbi_numeric": r.Vbi_numeric,
                    "W_numeric": r.W_numeric,
                    "Emax_numeric": r.Emax_numeric,
                    "newton_iterations": r.newton_iterations,
                    "converged": r.converged,
                    "validation_pass": validation_run_passed(r.validation),
                    "stop_reason": r.stop_reason,
                })
        return summary_path

    def save_sweep_summary(self, sweep: PnSweepResult) -> Path:
        summary_path = self.run_dir / "sweep_summary.csv"
        fieldnames = [
            "Vapp", "W", "W_psi", "W_rho", "Cj", "Emax", "Vbi",
            "converged", "newton_iterations",
        ]
        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in sweep.points:
                writer.writerow({
                    "Vapp": p.Vapp,
                    "W": p.W,
                    "W_psi": p.W_psi,
                    "W_rho": p.W_rho,
                    "Cj": p.Cj,
                    "Emax": p.Emax,
                    "Vbi": p.Vbi,
                    "converged": p.converged,
                    "newton_iterations": p.newton_iterations,
                })
        with open(self.run_dir / "sweep_results.json", "w", encoding="utf-8") as f:
            json.dump(sweep.model_dump(mode="json"), f, indent=2)
        return summary_path

    def save_optimization_summary(
        self,
        results: list[PnTrialResult],
        best: PnTrialResult | None,
    ) -> Path:
        summary_path = self.run_dir / "optimization_summary.csv"
        fieldnames = [
            "trial_index", "Na", "Nd", "Nx", "Vapp",
            "W_numeric", "W_rho_numeric", "Emax_numeric", "newton_iterations",
            "converged", "is_best",
        ]
        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow({
                    "trial_index": r.trial_index,
                    "Na": r.input.Na,
                    "Nd": r.input.Nd,
                    "Nx": r.input.Nx,
                    "Vapp": r.input.Vapp,
                    "W_numeric": r.W_numeric,
                    "W_rho_numeric": r.W_rho_numeric,
                    "Emax_numeric": r.Emax_numeric,
                    "newton_iterations": r.newton_iterations,
                    "converged": r.converged,
                    "is_best": best is not None and r.trial_index == best.trial_index,
                })
        return summary_path

    @property
    def plots_dir(self) -> Path:
        return self.run_dir / "plots"
