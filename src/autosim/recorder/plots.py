"""Matplotlib visualization for simulation results."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from autosim.schemas import TrialResult


def plot_trajectory(result: TrialResult, output_path: Path) -> None:
    if not result.trajectory:
        return

    times = [p.t for p in result.trajectory]
    ys = [p.y for p in result.trajectory]
    vs = [p.v for p in result.trajectory]
    drags = [p.drag_force for p in result.trajectory]

    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)

    axes[0].plot(times, ys, "b-", linewidth=1.5)
    axes[0].axhline(y=result.input.ground_y, color="k", linestyle="--", alpha=0.5)
    axes[0].set_ylabel("Position y (m)")
    axes[0].set_title(f"Trial {result.trial_index} Trajectory")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(times, vs, "g-", linewidth=1.5)
    axes[1].set_ylabel("Velocity v (m/s)")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(times, drags, "r-", linewidth=1.5)
    axes[2].set_ylabel("Drag force (N)")
    axes[2].set_xlabel("Time (s)")
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_convergence(results: list[TrialResult], output_path: Path) -> None:
    if not results:
        return

    indices = [r.trial_index for r in results]
    impact_times = [r.impact_time if r.impact_time is not None else float("nan") for r in results]
    max_vels = [
        max((abs(p.v) for p in r.probes), default=float("nan")) if r.probes else float("nan")
        for r in results
    ]

    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

    axes[0].plot(indices, impact_times, "bo-", linewidth=1.5, markersize=8)
    axes[0].set_ylabel("Impact time (s)")
    axes[0].set_title("Multi-trial Convergence")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(indices, max_vels, "ro-", linewidth=1.5, markersize=8)
    axes[1].set_ylabel("Max velocity (m/s)")
    axes[1].set_xlabel("Trial index")
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def generate_all_plots(results: list[TrialResult], plots_dir: Path) -> None:
    for result in results:
        plot_trajectory(
            result,
            plots_dir / f"trajectory_trial_{result.trial_index:03d}.png",
        )
    if len(results) > 1:
        plot_convergence(results, plots_dir / "convergence.png")
