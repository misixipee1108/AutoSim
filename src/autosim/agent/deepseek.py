"""DeepSeek API agent for structured simulation decisions."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from autosim.agent.rules import RulesAgent
from autosim.schemas import (
    AgentAction,
    AgentBackend,
    AgentConfig,
    AgentDecision,
    ProbeSnapshot,
    SimInput,
)


SYSTEM_PROMPT = """You are a physics simulation monitoring agent for a falling block with air drag.
Analyze probe snapshots and return a JSON decision with these fields:
- action: one of "continue", "early_stop", "adjust_search_space", "explain_failure", "recommend_next"
- reason: brief explanation
- confidence: float 0-1
- suggested_params: optional dict of parameter changes for next trial
- search_space_patch: optional dict narrowing parameter ranges

During mid-run monitoring, prefer "continue" unless simulation is clearly diverging or invalid.
After run completion, use "recommend_next" with suggested_params for the next iteration.
Return ONLY valid JSON, no markdown."""


class AgentService:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.rules = RulesAgent(config)
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    def evaluate_mid_run(
        self,
        probe: ProbeSnapshot,
        sim_input: SimInput,
        probe_history: list[ProbeSnapshot],
    ) -> AgentDecision:
        rules_decision = self.rules.evaluate_mid_run(probe, sim_input)

        if self.config.backend == AgentBackend.RULES:
            return rules_decision

        if self.config.backend in (AgentBackend.DEEPSEEK, AgentBackend.HYBRID):
            if not self.api_key:
                return rules_decision
            try:
                llm_decision = self._call_llm(
                    sim_input,
                    probe_history[-self.config.probe_window :],
                    phase="mid_run",
                )
                if self.config.backend == AgentBackend.HYBRID:
                    return self.rules.veto(llm_decision, probe)
                return llm_decision
            except Exception:
                return rules_decision

        return rules_decision

    def evaluate_post_run(
        self,
        sim_input: SimInput,
        probes: list[ProbeSnapshot],
        early_stopped: bool,
        stop_reason: str,
    ) -> AgentDecision:
        rules_decision = self.rules.evaluate_post_run(
            sim_input, probes, early_stopped, stop_reason
        )

        if self.config.backend == AgentBackend.RULES:
            return rules_decision

        if self.config.backend in (AgentBackend.DEEPSEEK, AgentBackend.HYBRID):
            if not self.api_key:
                return rules_decision
            try:
                return self._call_llm(
                    sim_input,
                    probes[-self.config.probe_window :],
                    phase="post_run",
                    extra={"early_stopped": early_stopped, "stop_reason": stop_reason},
                )
            except Exception:
                return rules_decision

        return rules_decision

    def _call_llm(
        self,
        sim_input: SimInput,
        recent_probes: list[ProbeSnapshot],
        phase: str,
        extra: dict[str, Any] | None = None,
    ) -> AgentDecision:
        user_content = {
            "phase": phase,
            "sim_input": sim_input.model_dump(mode="json"),
            "recent_probes": [p.model_dump(mode="json") for p in recent_probes],
            "extra": extra or {},
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url.rstrip('/')}/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        action_str = parsed.get("action", "continue")
        try:
            action = AgentAction(action_str)
        except ValueError:
            action = AgentAction.CONTINUE

        return AgentDecision(
            action=action,
            reason=parsed.get("reason", "LLM decision"),
            confidence=float(parsed.get("confidence", 0.5)),
            suggested_params=parsed.get("suggested_params"),
            search_space_patch=parsed.get("search_space_patch"),
        )
