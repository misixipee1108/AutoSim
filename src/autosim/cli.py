"""Command-line interface for AutoSim."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from autosim.orchestrator.pn_runner import run_pn_iteration, run_pn_trial, run_pn_with_sweep
from autosim.orchestrator.pn_optimizer import run_pn_optimization
from autosim.orchestrator.runner import run_iteration, run_trial
from autosim.pn.schemas import PnRunConfig
from autosim.recorder.logger import RunRecorder
from autosim.recorder.plots import generate_all_plots
from autosim.recorder.pn_logger import PnRunRecorder
from autosim.recorder.pn_plots import generate_pn_plots, plot_sweep_curves
from autosim.schemas import AgentBackend, RunConfig


def load_falling_config(path: str | Path) -> RunConfig:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return RunConfig.model_validate(data)


def load_pn_config(path: str | Path) -> PnRunConfig:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return PnRunConfig.model_validate(data)


def cmd_run(args: argparse.Namespace) -> int:
    if args.sim == "pn":
        return _cmd_pn_run(args)
    return _cmd_falling_run(args)


def cmd_iterate(args: argparse.Namespace) -> int:
    if args.sim == "pn":
        return _cmd_pn_iterate(args)
    return _cmd_falling_iterate(args)


def _cmd_falling_run(args: argparse.Namespace) -> int:
    config = load_falling_config(args.config)
    sim_input = config.to_sim_input()
    if args.agent:
        sim_input.agent.backend = AgentBackend(args.agent)
    recorder = RunRecorder(args.output)
    result = run_trial(sim_input)
    recorder.save_trial(result)
    generate_all_plots([result], recorder.plots_dir)
    print(f"Run complete. Output: {recorder.run_dir}")
    print(f"  Impact time: {result.impact_time}")
    print(f"  Impact velocity: {result.impact_velocity}")
    return 0


def _cmd_falling_iterate(args: argparse.Namespace) -> int:
    config = load_falling_config(args.config)
    sim_input = config.to_sim_input()
    if args.agent:
        sim_input.agent.backend = AgentBackend(args.agent)
    if args.max_trials:
        sim_input.iteration.max_trials = args.max_trials
    recorder = RunRecorder(args.output)
    results = run_iteration(sim_input)
    for result in results:
        recorder.save_trial(result)
    summary_path = recorder.save_summary(results)
    generate_all_plots(results, recorder.plots_dir)
    print(f"Iteration complete. {len(results)} trial(s). Output: {recorder.run_dir}")
    print(f"  Summary: {summary_path}")
    return 0


def cmd_optimize(args: argparse.Namespace) -> int:
    if args.sim != "pn":
        print("Optimization is currently supported for --sim pn only.", file=sys.stderr)
        return 1
    return _cmd_pn_optimize(args)


def cmd_benchmark(args: argparse.Namespace) -> int:
    if args.sim != "pn":
        print("Benchmarks currently supported for --sim pn only.", file=sys.stderr)
        return 1
    from autosim.pn.benchmarks import list_benchmark_cases, run_benchmark

    cases = [args.case] if args.case else list_benchmark_cases()
    if not cases:
        print("No benchmark cases found.", file=sys.stderr)
        return 1
    failed = 0
    for name in cases:
        result = run_benchmark(name)
        status = "PASS" if result["all_passed"] else "FAIL"
        print(f"[{status}] {name}: {result['checks']}")
        if not result["all_passed"]:
            failed += 1
    return 1 if failed else 0


def _cmd_pn_run(args: argparse.Namespace) -> int:
    config = load_pn_config(args.config)
    sim_input = config.to_sim_input()
    if args.agent:
        sim_input.agent.backend = AgentBackend(args.agent)
    recorder = PnRunRecorder(args.output)

    if sim_input.bias_scan.enabled or getattr(args, "sweep", False):
        sim_input.bias_scan.enabled = True
        results, sweep = run_pn_with_sweep(sim_input)
        for result in results:
            recorder.save_trial(result)
        sweep_path = recorder.save_sweep_summary(sweep)
        generate_pn_plots(results, recorder.plots_dir)
        if sweep.points:
            plot_sweep_curves(sweep, recorder.plots_dir / "sweep_curves.png")
        validation_path = recorder.save_validation_report(results)
        print(f"PN bias sweep complete. Output: {recorder.run_dir}")
        print(f"  Points: {len(sweep.points)}, all converged: {sweep.all_converged}")
        print(f"  Sweep summary: {sweep_path}")
        print(f"  Validation: {validation_path}")
        return 0

    result = run_pn_trial(sim_input)
    recorder.save_trial(result)
    generate_pn_plots([result], recorder.plots_dir)
    validation_path = recorder.save_validation_report([result])
    print(f"PN run complete. Output: {recorder.run_dir}")
    print(f"  Vbi: {result.Vbi_numeric:.4f} V")
    print(f"  W: {result.W_numeric:.2e} cm (rho method)")
    print(f"  Converged: {result.converged}")
    print(f"  Validation: {validation_path}")
    return 0


def _cmd_pn_optimize(args: argparse.Namespace) -> int:
    config = load_pn_config(args.config)
    sim_input = config.to_sim_input()
    if args.agent:
        sim_input.agent.backend = AgentBackend(args.agent)
    sim_input.optimization.enabled = True
    if args.max_trials:
        sim_input.optimization.max_trials = args.max_trials
    recorder = PnRunRecorder(args.output)
    results, best = run_pn_optimization(sim_input)
    for result in results:
        recorder.save_trial(result)
    summary_path = recorder.save_optimization_summary(results, best)
    validation_path = recorder.save_validation_report(results)
    generate_pn_plots(results, recorder.plots_dir)
    print(f"PN optimization complete. {len(results)} trial(s). Output: {recorder.run_dir}")
    print(f"  Summary: {summary_path}")
    print(f"  Validation: {validation_path}")
    if best:
        print(f"  Best W: {best.W_numeric:.2e} cm, Emax: {best.Emax_numeric:.2e} V/cm")
    return 0


def _cmd_pn_iterate(args: argparse.Namespace) -> int:
    config = load_pn_config(args.config)
    sim_input = config.to_sim_input()
    if args.agent:
        sim_input.agent.backend = AgentBackend(args.agent)
    if args.max_trials:
        sim_input.iteration.max_trials = args.max_trials
    recorder = PnRunRecorder(args.output)
    results = run_pn_iteration(sim_input)
    for result in results:
        recorder.save_trial(result)
    summary_path = recorder.save_summary(results)
    validation_path = recorder.save_validation_report(results)
    generate_pn_plots(results, recorder.plots_dir)
    print(f"PN iteration complete. {len(results)} trial(s). Output: {recorder.run_dir}")
    print(f"  Summary: {summary_path}")
    print(f"  Validation: {validation_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="autosim", description="AutoSim physics simulation")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in [("run", "Run a single simulation trial"), ("iterate", "Run multi-trial iteration")]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("-c", "--config", required=True, help="Path to YAML config")
        p.add_argument(
            "--sim",
            choices=["falling_block", "pn"],
            default="falling_block",
            help="Simulation type",
        )
        p.add_argument(
            "--agent",
            choices=["rules", "deepseek", "hybrid"],
            help="Override agent backend",
        )
        p.add_argument("-o", "--output", default="runs", help="Output directory")
        if name == "run":
            p.add_argument(
                "--sweep",
                action="store_true",
                help="Run bias sweep (PN only; also enabled via bias_scan.enabled in config)",
            )
        if name == "iterate":
            p.add_argument("--max-trials", type=int, help="Override max trials")
        p.set_defaults(func=cmd_run if name == "run" else cmd_iterate)

    opt = sub.add_parser("optimize", help="Run parameter optimization (PN)")
    opt.add_argument("-c", "--config", required=True, help="Path to YAML config")
    opt.add_argument("--sim", choices=["pn"], default="pn", help="Simulation type")
    opt.add_argument(
        "--agent",
        choices=["rules", "deepseek", "hybrid"],
        help="Override agent backend",
    )
    opt.add_argument("-o", "--output", default="runs", help="Output directory")
    opt.add_argument("--max-trials", type=int, help="Override optimization max trials")
    opt.set_defaults(func=cmd_optimize)

    bench = sub.add_parser("benchmark", help="Run PN benchmark cases")
    bench.add_argument("--sim", choices=["pn"], default="pn")
    bench.add_argument("--case", help="Specific benchmark case name")
    bench.set_defaults(func=cmd_benchmark)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
