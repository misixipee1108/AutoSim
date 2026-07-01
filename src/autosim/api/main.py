"""FastAPI application for AutoSim frontend."""

from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from autosim.api.model_registry.registry import get_model, list_models
from autosim.api.run_manager import run_manager
from autosim.api.schemas import CreateRunRequest, CreateRunResponse, ModelDescriptor, UnifiedRunResult

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


@app.get("/api/models", response_model=list[ModelDescriptor])
def api_list_models() -> list[ModelDescriptor]:
    return list_models()


@app.get("/api/models/{model_id}", response_model=ModelDescriptor)
def api_get_model(model_id: str) -> ModelDescriptor:
    try:
        return get_model(model_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/runs", response_model=CreateRunResponse)
def api_create_run(request: CreateRunRequest) -> CreateRunResponse:
    try:
        get_model(request.model_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    state = run_manager.create_run(request)
    return CreateRunResponse(run_id=state.run_id, model_id=state.model_id, status=state.status)


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
