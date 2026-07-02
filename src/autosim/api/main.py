"""FastAPI application for AutoSim frontend."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from fastapi.responses import PlainTextResponse

from autosim.api.benchmark_store import (
    display_category,
    get_report,
    get_report_markdown,
    list_reports,
    validation_status_display,
)
from autosim.api.run_manager import run_manager
from autosim.api.schemas import (
    BenchmarkCaseReportEnriched,
    BenchmarkEnvironmentView,
    BenchmarkReportEnriched,
    BenchmarkReportListItem,
    BenchmarkSummaryView,
    CreateRunRequest,
    CreateRunResponse,
    ModelTreeSchemaResponse,
    PhysicsInterfaceListItem,
    ProjectParameterSchemaResponse,
    ProjectTemplateListItem,
    UnifiedRunResult,
)
from autosim.plugins.registry import list_physics_descriptors, list_study_types
from autosim.project.loader import default_pn_stationary_project
from autosim.project.parameter_schema import parameters_for_tree_path
from autosim.project.schemas import SimulationProject as SimulationProjectSchema
from autosim.project.templates import get_template, list_template_ids
from autosim.project.tree_schema import build_model_tree_schema

app = FastAPI(title="AutoSim API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/models")
def api_list_models_deprecated() -> None:
    raise HTTPException(
        status_code=410,
        detail="GET /api/models removed. Use GET /api/project/templates and GET /api/plugins/physics.",
    )


@app.get("/api/models/{model_id}")
def api_get_model_deprecated(model_id: str) -> None:
    raise HTTPException(
        status_code=410,
        detail=f"Legacy model descriptor '{model_id}' removed. Use project templates.",
    )


@app.post("/api/runs", response_model=CreateRunResponse)
def api_create_run(request: CreateRunRequest) -> CreateRunResponse:
    if not request.project:
        raise HTTPException(
            status_code=400,
            detail="project payload required. Legacy model_id/config no longer supported.",
        )
    project = SimulationProjectSchema.model_validate(request.project)
    model_id = project.project_id
    try:
        state = run_manager.create_run(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CreateRunResponse(run_id=state.run_id, model_id=model_id, status=state.status)


@app.get("/api/project/tree-schema", response_model=ModelTreeSchemaResponse)
def api_project_tree_schema() -> ModelTreeSchemaResponse:
    tree = build_model_tree_schema(default_pn_stationary_project())
    return ModelTreeSchemaResponse(**tree)


@app.get("/api/project/templates", response_model=list[ProjectTemplateListItem])
def api_list_project_templates() -> list[ProjectTemplateListItem]:
    items: list[ProjectTemplateListItem] = []
    for tid in list_template_ids():
        project = get_template(tid)
        items.append(
            ProjectTemplateListItem(
                template_id=tid,
                project_id=project.project_id,
                title=project.title,
                active_study_id=project.active_study_id,
            )
        )
    return items


@app.get("/api/project/templates/{template_id}", response_model=SimulationProjectSchema)
def api_get_project_template(template_id: str) -> SimulationProjectSchema:
    try:
        return get_template(template_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/project/templates/pn_stationary", response_model=SimulationProjectSchema)
def api_pn_stationary_template() -> SimulationProjectSchema:
    return default_pn_stationary_project()


@app.get("/api/plugins/studies")
def api_list_study_types() -> dict[str, list[str]]:
    return {"study_types": list_study_types()}


@app.post("/api/project/tree-schema", response_model=ModelTreeSchemaResponse)
def api_project_tree_schema_for_project(project: SimulationProjectSchema) -> ModelTreeSchemaResponse:
    tree = build_model_tree_schema(project)
    return ModelTreeSchemaResponse(**tree)


@app.post("/api/project/parameters", response_model=ProjectParameterSchemaResponse)
def api_project_parameters(
    project: SimulationProjectSchema,
    tree_path: str,
) -> ProjectParameterSchemaResponse:
    params = parameters_for_tree_path(project, tree_path)
    return ProjectParameterSchemaResponse(tree_path=tree_path, parameters=params)


@app.get("/api/plugins/physics", response_model=list[PhysicsInterfaceListItem])
def api_list_physics_plugins() -> list[PhysicsInterfaceListItem]:
    return [
        PhysicsInterfaceListItem(
            interface_id=d.interface_id,
            name=d.name,
            category=d.category,
            dimension=d.dimension,
            governing_equations=d.governing_equations,
        )
        for d in list_physics_descriptors()
    ]


@app.get("/api/runs/{run_id}", response_model=UnifiedRunResult)
def api_get_run(run_id: str) -> UnifiedRunResult:
    state = run_manager.get_run(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    if state.result is not None:
        state.result.logs = state.logs
        state.result.status = state.status
        return state.result
    return UnifiedRunResult(
        run_id=run_id,
        model_id=state.model_id,
        status=state.status,
        logs=state.logs,
        error=state.error,
    )


@app.get("/api/runs/{run_id}/stream")
async def api_stream_run(run_id: str) -> EventSourceResponse:
    state = run_manager.get_run(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    queue = run_manager.subscribe(run_id)
    if queue is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    async def event_generator():
        yield {"event": "status", "data": json.dumps({"status": state.status.value})}
        for log_line in state.logs:
            yield {"event": "log", "data": json.dumps({"message": log_line})}
        if state.result and state.status.value in ("completed", "failed", "early_stopped"):
            yield {"event": "complete", "data": json.dumps(state.result.model_dump(mode="json"))}
            return

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield {"event": event.event, "data": json.dumps(event.data)}
                if event.event in ("complete", "error"):
                    break
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "{}"}

    return EventSourceResponse(event_generator())


def _enrich_report(report) -> BenchmarkReportEnriched:
    cases = [
        BenchmarkCaseReportEnriched(
            **c.model_dump(),
            validation_status_display=validation_status_display(c.validation_status),
            display_category=display_category(c),
        )
        for c in report.case_results
    ]
    return BenchmarkReportEnriched(
        schema_version=report.schema_version,
        run_id=report.run_id,
        timestamp=report.timestamp,
        git_commit=report.git_commit,
        benchmark_suite=report.benchmark_suite,
        autosim_version=report.autosim_version,
        output_dir=report.output_dir,
        environment=BenchmarkEnvironmentView(**report.environment.model_dump()),
        summary=BenchmarkSummaryView(**report.summary.model_dump()),
        case_results=cases,
    )


@app.post("/api/benchmarks/run")
def api_run_benchmarks() -> dict[str, Any]:
    """Run full PN benchmark suite and write reports to disk."""
    from autosim.pn.benchmarks import run_benchmark_suite

    suite = run_benchmark_suite()
    return {
        "run_id": suite.run_id,
        "overall_passed": suite.summary.overall_passed,
        "total": suite.summary.total,
        "passed_count": suite.summary.passed_count,
        "warning_count": suite.summary.warning_count,
        "failed_count": suite.summary.failed_count,
        "total_runtime_s": suite.summary.total_runtime_s,
        "output_dir": str(suite.output_dir),
    }


@app.get("/api/benchmarks/reports", response_model=list[BenchmarkReportListItem])
def api_list_benchmark_reports() -> list[BenchmarkReportListItem]:
    return [
        BenchmarkReportListItem(
            run_id=r.run_id,
            timestamp=r.timestamp,
            git_commit=r.git_commit,
            benchmark_suite=r.benchmark_suite,
            output_dir=r.output_dir,
            total=r.summary.total,
            passed_count=r.summary.passed_count,
            warning_count=r.summary.warning_count,
            failed_count=r.summary.failed_count,
            total_runtime_s=r.summary.total_runtime_s,
            overall_passed=r.summary.overall_passed,
        )
        for r in list_reports()
    ]


@app.get("/api/benchmarks/reports/{run_id}", response_model=BenchmarkReportEnriched)
def api_get_benchmark_report(run_id: str) -> BenchmarkReportEnriched:
    report = get_report(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Benchmark report not found: {run_id}")
    return _enrich_report(report)


@app.get("/api/benchmarks/reports/{run_id}/markdown")
def api_get_benchmark_report_markdown(run_id: str) -> PlainTextResponse:
    md = get_report_markdown(run_id)
    if md is None:
        raise HTTPException(status_code=404, detail=f"Benchmark markdown not found: {run_id}")
    return PlainTextResponse(content=md, media_type="text/markdown; charset=utf-8")
