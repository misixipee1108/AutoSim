"""Simulation adapter protocol and shared utilities."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from pydantic import BaseModel

from autosim.api.schemas import (
    UnifiedAgentDecision,
    UnifiedProbe,
    UnifiedRunResult,
)


class RunCallbacks:
    def __init__(
        self,
        on_probe: Callable[[UnifiedProbe], None] | None = None,
        on_decision: Callable[[UnifiedAgentDecision], None] | None = None,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self.on_probe = on_probe
        self.on_decision = on_decision
        self.on_log = on_log


class SimAdapter(Protocol):
    model_id: str

    def validate_config(self, raw: dict[str, Any]) -> BaseModel: ...

    def run_trial(
        self,
        config: BaseModel,
        trial_index: int,
        callbacks: RunCallbacks | None = None,
    ) -> Any: ...

    def run_iteration(
        self,
        config: BaseModel,
        callbacks: RunCallbacks | None = None,
    ) -> list[Any]: ...

    def normalize_result(
        self,
        run_id: str,
        raw: Any,
        status: str = "completed",
        logs: list[str] | None = None,
    ) -> UnifiedRunResult: ...

    def normalize_probe(self, raw: Any) -> UnifiedProbe: ...

    def normalize_decision(self, raw: Any) -> UnifiedAgentDecision: ...


def flatten_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert dotted parameter names to nested dict."""
    result: dict[str, Any] = {}
    for key, value in raw.items():
        parts = key.split(".")
        if len(parts) == 1:
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = {**result[key], **value}
            else:
                result[key] = value
        else:
            cursor = result
            for part in parts[:-1]:
                cursor = cursor.setdefault(part, {})
            cursor[parts[-1]] = value
    return result


def apply_agent_override(config: dict[str, Any], agent: str | None) -> dict[str, Any]:
    if agent:
        config.setdefault("agent", {})
        if isinstance(config["agent"], dict):
            config["agent"]["backend"] = agent
    return config
