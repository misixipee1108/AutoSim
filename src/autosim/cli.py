"""Command-line interface for AutoSim (v2 project-only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from autosim.api.adapters.project import ProjectAdapter
from autosim.project.loader import load_project, load_project_json
from autosim.project.yaml_converter import falling_yaml_to_project, pn_yaml_to_project
from autosim.recorder.project_recorder import ProjectRunRecorder


def _load_project_from_path(path: str | Path):
    path = Path(path)
    if path.suffix.lower() in (".json",):
        return load_project_json(path)
    if path.suffix.lower() in (".yaml", ".yml"):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict) and data.get("schema_version") == "2.0":
            return load_project(path)
        if "mass" in data and "gravity" in data:
            return falling_yaml_to_project(path)
        return pn_yaml_to_project(path)
    raise ValueError(f"Unsupported project file: {path}")


def cmd_run(args: argparse.Namespace) -> int:
    project_path = args.project or args.config
    if not project_path:
        print("Provide --project or --config path.", file=sys.stderr)
        return 1
    project = _load_project_from_path(project_path)
    if args.agent and project.studies:
        study = project.studies[0]
        if study.agent:
            studies = [
                s.model_copy(update={"agent": s.agent.model_copy(update={"backend": args.agent})})
                if s.study_id == study.study_id
                else s
                for s in project.studies
            ]
            project = project.model_copy(update={"studies": studies})

    adapter = ProjectAdapter()
    raw = adapter.run_study(project, max_trials=args.max_trials or 1)
    recorder = ProjectRunRecorder(args.output)
    out_dir = recorder.save(project, raw)
    print(f"Run complete. Output: {out_dir}")
    print(f"  Project: {project.project_id}")
    print(f"  Study: {project.active_study_id}")
    return 0


def cmd_export_yaml(args: argparse.Namespace) -> int:
    """Convert legacy YAML demo to v2 project JSON."""
    project = _load_project_from_path(args.config)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(project.model_dump(mode="json"), f, indent=2)
    print(f"Exported: {out}")
    return 0


def cmd_benchmark_pn(args: argparse.Namespace) -> int:
    from autosim.pn.benchmark_report import default_output_dir
    from autosim.pn.benchmarks import list_benchmark_cases, run_benchmark_suite

    cases = [args.case] if args.case else None
    if args.case and args.case not in list_benchmark_cases():
        print(f"Benchmark case not found: {args.case}", file=sys.stderr)
        return 1
    output_dir = Path(args.output) if args.output else default_output_dir()
    suite = run_benchmark_suite(case_ids=cases, output_dir=output_dir)
    for case in suite.cases:
        label = case.outcome.upper()
        print(f"[{label}] {case.case_id} ({case.elapsed_s:.2f}s) — {case.run_status}")
    s = suite.summary
    print(f"\nSummary: {s.passed} passed, {s.warnings} warnings, {s.failed} failed")
    return 1 if suite.summary.failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="autosim", description="AutoSim v2 simulation CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run a SimulationProject (JSON or legacy YAML)")
    run_p.add_argument("-p", "--project", help="Path to v2 project JSON")
    run_p.add_argument("-c", "--config", help="Path to YAML (legacy) or project file")
    run_p.add_argument(
        "--agent",
        choices=["rules", "deepseek", "hybrid"],
        help="Override agent backend",
    )
    run_p.add_argument("--max-trials", type=int, default=1, help="Multi-trial iteration count")
    run_p.add_argument("-o", "--output", default="runs", help="Output directory")
    run_p.set_defaults(func=cmd_run)

    export_p = sub.add_parser("export-project", help="Convert legacy YAML to v2 project JSON")
    export_p.add_argument("-c", "--config", required=True, help="Legacy YAML config")
    export_p.add_argument("-o", "--output", required=True, help="Output JSON path")
    export_p.set_defaults(func=cmd_export_yaml)

    bench = sub.add_parser("benchmark", help="Run benchmark suites")
    bench_sub = bench.add_subparsers(dest="suite", required=True)
    pn_bench = bench_sub.add_parser("pn", help="PN junction benchmark suite")
    pn_bench.add_argument("--case", help="Specific benchmark case name")
    pn_bench.add_argument("-o", "--output", help="Output directory")
    pn_bench.set_defaults(func=cmd_benchmark_pn)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
