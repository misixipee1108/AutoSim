"""DeepSeek agent for PN junction simulations."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from autosim.agent.pn_rules import PnRulesAgent
from autosim.pn.schemas import (
    PnAgentAction,
    PnAgentConfig,
    PnAgentDecision,
    PnNewtonProbe,
    PnSimInput,
)
from autosim.schemas import AgentBackend


PN_SYSTEM_PROMPT = """You are a semiconductor PN junction Poisson solver monitoring agent.
Analyze Newton iteration probes for a 1D drift-diffusion-free Poisson simulation.
Return JSON with fields:
- action: one of "continue", "early_stop", "adjust_damping", "refine_mesh",
  "adjust_bias_step", "change_initial_guess", "mark_as_infeasible",
  "explain_failure", "recommend_next_parameters"
- reason: brief explanation
- confidence: float 0-1
- suggested_params: optional dict (damping, Nx, Vapp, tol, etc.)

During Newton iterations prefer "continue" unless diverging, NaN, or clearly stalled.
After completion use "recommend_next_parameters" for next trial.
Return ONLY valid JSON."""


class PnAgentService:
    def __init__(self, config: PnAgentConfig) -> None:
        self.config = config
        self.rules = PnRulesAgent(config)
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    def evaluate_mid_run(
        self,
        probe: PnNewtonProbe,
        sim_input: PnSimInput,
        probe_history: list[PnNewtonProbe],
    ) -> PnAgentDecision:
        rules_decision = self.rules.evaluate_mid_run(probe, sim_input)
        if self.config.backend == AgentBackend.RULES:
            return rules_decision
        if self.config.backend in (AgentBackend.DEEPSEEK, AgentBackend.HYBRID):
            if not self.api_key:
                return rules_decision
            try:
                llm_decision = self._call_llm(
                    sim_input, probe_history[-self.config.probe_window :], "mid_run"
                )
                if self.config.backend == AgentBackend.HYBRID:
                    return self.rules.veto(llm_decision, probe)
                return llm_decision
            except Exception:
                return rules_decision
        return rules_decision

    def evaluate_post_run(
        self,
        sim_input: PnSimInput,
        probes: list[PnNewtonProbe],
        converged: bool,
        stop_reason: str,
    ) -> PnAgentDecision:
        rules_decision = self.rules.evaluate_post_run(
            sim_input, probes, converged, stop_reason
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
                    "post_run",
                    extra={"converged": converged, "stop_reason": stop_reason},
                )
            except Exception:
                return rules_decision
        return rules_decision

    def _call_llm(
        self,
        sim_input: PnSimInput,
        recent_probes: list[PnNewtonProbe],
        phase: str,
        extra: dict[str, Any] | None = None,
    ) -> PnAgentDecision:
        user_content = {
            "phase": phase,
            "sim_input": sim_input.model_dump(mode="json"),
            "recent_probes": [p.model_dump(mode="json") for p in recent_probes],
            "extra": extra or {},
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": PN_SYSTEM_PROMPT},
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
        try:
            action = PnAgentAction(parsed.get("action", "continue"))
        except ValueError:
            action = PnAgentAction.CONTINUE
        return PnAgentDecision(
            action=action,
            reason=parsed.get("reason", "LLM decision"),
            confidence=float(parsed.get("confidence", 0.5)),
            suggested_params=parsed.get("suggested_params"),
        )
