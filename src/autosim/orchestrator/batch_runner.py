"""Batch experiment runner for PN simulations."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autosim.orchestrator.pn_optimizer import run_pn_optimization
from autosim.orchestrator.pn_runner import run_pn_iteration, run_pn_with_sweep
from autosim.pn.schemas import PnSimInput, PnTrialResult


@dataclass
class BatchTask:
    task_id: str
    task_type: str  # sweep | optimize | iterate
    config: PnSimInput
    status: str = "pending"
    results: list[PnTrialResult] = field(default_factory=list)
    error: str | None = None


class BatchRunner:
    def __init__(self, output_dir: str | Path = "runs/batch") -> None:
        self.output_dir = Path(output_dir)
        self.tasks: list[BatchTask] = []

    def submit(self, task_type: str, config: PnSimInput) -> BatchTask:
        task_id = f"{task_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        task = BatchTask(task_id=task_id, task_type=task_type, config=config)
        self.tasks.append(task)
        return task

    def run_task(self, task: BatchTask) -> BatchTask:
        task.status = "running"
        try:
            if task.task_type == "sweep":
                results, _ = run_pn_with_sweep(task.config)
                task.results = results
            elif task.task_type == "optimize":
                results, _ = run_pn_optimization(task.config)
                task.results = results
            else:
                task.results = run_pn_iteration(task.config)
            task.status = "completed"
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
        self._persist(task)
        return task

    def run_all(self) -> list[BatchTask]:
        return [self.run_task(t) for t in self.tasks if t.status == "pending"]

    def _persist(self, task: BatchTask) -> Path:
        task_dir = self.output_dir / task.task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "status": task.status,
            "error": task.error,
            "n_results": len(task.results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(task_dir / "task.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        return task_dir

    @staticmethod
    def load_index(output_dir: str | Path = "runs/batch") -> list[dict[str, Any]]:
        root = Path(output_dir)
        if not root.exists():
            return []
        entries = []
        for p in sorted(root.glob("*/task.json"), reverse=True):
            with open(p, encoding="utf-8") as f:
                entries.append(json.load(f))
        return entries
