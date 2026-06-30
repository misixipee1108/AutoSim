"""Command-line interface for AutoSim."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from autosim.orchestrator.runner import run_iteration, run_trial
from autosim.recorder.logger import RunRecorder
from autosim.recorder.plots import generate_all_plots
from autosim.schemas import AgentBackend, RunConfig


def load_config(path: str | Path) -> RunConfig:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return RunConfig.model_validate(data)


def cmd_run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
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
    print(f"  Early stopped: {result.early_stopped}")
    return 0


def cmd_iterate(args: argparse.Namespace) -> int:
    config = load_config(args.config)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="autosim", description="AutoSim physics simulation")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run a single simulation trial")
    run_parser.add_argument("-c", "--config", required=True, help="Path to YAML config")
    run_parser.add_argument(
        "--agent",
        choices=["rules", "deepseek", "hybrid"],
        help="Override agent backend",
    )
    run_parser.add_argument("-o", "--output", default="runs", help="Output directory")
    run_parser.set_defaults(func=cmd_run)

    iter_parser = sub.add_parser("iterate", help="Run multi-trial iteration")
    iter_parser.add_argument("-c", "--config", required=True, help="Path to YAML config")
    iter_parser.add_argument(
        "--agent",
        choices=["rules", "deepseek", "hybrid"],
        help="Override agent backend",
    )
    iter_parser.add_argument(
        "--max-trials",
        type=int,
        help="Override max trials from config",
    )
    iter_parser.add_argument("-o", "--output", default="runs", help="Output directory")
    iter_parser.set_defaults(func=cmd_iterate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
