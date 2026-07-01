"""Matplotlib plots for PN junction results."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from autosim.pn.schemas import PnSweepResult, PnTrialResult


def plot_psi(result: PnTrialResult, output_path: Path) -> None:
    if not result.profile:
        return
    x = [p.x * 1e4 for p in result.profile]
    psi = [p.psi for p in result.profile]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x, psi, "b-", linewidth=1.5)
    ax.set_xlabel("Position (um)")
    ax.set_ylabel("Potential psi (V)")
    ax.set_title(f"Trial {result.trial_index} Potential Profile")
    ax.grid(True, alpha=0.3)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_electric_field(result: PnTrialResult, output_path: Path) -> None:
    if not result.profile:
        return
    x = [p.x * 1e4 for p in result.profile]
    E = [p.E for p in result.profile]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x, E, "r-", linewidth=1.5)
    ax.set_xlabel("Position (um)")
    ax.set_ylabel("Electric field (V/cm)")
    ax.set_title(f"Trial {result.trial_index} Electric Field")
    ax.grid(True, alpha=0.3)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_carriers(result: PnTrialResult, output_path: Path) -> None:
    if not result.profile:
        return
    x = [p.x * 1e4 for p in result.profile]
    n = [max(p.n, 1.0) for p in result.profile]
    p_vals = [max(p.p, 1.0) for p in result.profile]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.semilogy(x, n, "g-", label="n", linewidth=1.5)
    ax.semilogy(x, p_vals, "m-", label="p", linewidth=1.5)
    ax.set_xlabel("Position (um)")
    ax.set_ylabel("Carrier density (cm^-3)")
    ax.set_title(f"Trial {result.trial_index} Carrier Concentrations")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_newton_residual(result: PnTrialResult, output_path: Path) -> None:
    if not result.probes:
        return
    iters = [p.iteration for p in result.probes]
    residuals = [p.residual_norm for p in result.probes]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.semilogy(iters, residuals, "ko-", markersize=4)
    ax.set_xlabel("Newton iteration")
    ax.set_ylabel("Residual norm")
    ax.set_title(f"Trial {result.trial_index} Newton Convergence")
    ax.grid(True, alpha=0.3)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_pn_convergence(results: list[PnTrialResult], output_path: Path) -> None:
    if not results:
        return
    indices = [r.trial_index for r in results]
    iters = [r.newton_iterations for r in results]
    vbi_err = [
        r.validation.Vbi.rel_error if r.validation and r.validation.Vbi else float("nan")
        for r in results
    ]
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].plot(indices, iters, "bo-", markersize=8)
    axes[0].set_ylabel("Newton iterations")
    axes[0].set_title("Multi-trial PN Convergence")
    axes[0].grid(True, alpha=0.3)
    axes[1].plot(indices, vbi_err, "ro-", markersize=8)
    axes[1].set_ylabel("Vbi rel error")
    axes[1].set_xlabel("Trial index")
    axes[1].grid(True, alpha=0.3)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_sweep_curves(sweep: PnSweepResult, output_path: Path) -> None:
    if not sweep.points:
        return
    vapp = [p.Vapp for p in sweep.points]
    w = [p.W or float("nan") for p in sweep.points]
    cj = [p.Cj or float("nan") for p in sweep.points]
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].plot(vapp, [wi * 1e4 for wi in w], "b-o", markersize=4)
    axes[0].set_ylabel("W (um)")
    axes[0].set_title("Depletion Width vs Applied Bias")
    axes[0].grid(True, alpha=0.3)
    axes[1].plot(vapp, cj, "r-o", markersize=4)
    axes[1].set_ylabel("Cj (F/cm²)")
    axes[1].set_xlabel("Vapp (V)")
    axes[1].set_title("Junction Capacitance vs Applied Bias")
    axes[1].grid(True, alpha=0.3)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def generate_pn_plots(results: list[PnTrialResult], plots_dir: Path) -> None:
    for result in results:
        idx = result.trial_index
        plot_psi(result, plots_dir / f"psi_trial_{idx:03d}.png")
        plot_electric_field(result, plots_dir / f"E_trial_{idx:03d}.png")
        plot_carriers(result, plots_dir / f"carriers_trial_{idx:03d}.png")
        plot_newton_residual(result, plots_dir / f"newton_residual_trial_{idx:03d}.png")
    if len(results) > 1:
        plot_pn_convergence(results, plots_dir / "convergence.png")
