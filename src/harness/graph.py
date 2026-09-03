from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from langgraph.graph import END, START, StateGraph

from src.runtime import CheckpointConfig, CheckpointerFactory
from .nodes import context, executor, planner, synthesizer, understand, verifier
from .state import HarnessState, create_initial_state


@dataclass
class HarnessExecutionResult:
    success: bool
    message: str
    confidence: float
    trace: list
    chart_data: Dict[str, Any]
    state: Dict[str, Any]
    error: Optional[str] = None


class EvidenceDrivenHarness:
    CORE_NODES = ("understand", "context", "planner", "executor", "verifier", "synthesizer")

    def __init__(self, checkpointer=None):
        self.checkpointer = checkpointer or CheckpointerFactory.create(CheckpointConfig(
            backend=os.getenv("AGENT_CHECKPOINT_BACKEND", "memory"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            prefix=os.getenv("AGENT_CHECKPOINT_PREFIX", "oncall_harness"),
            ttl_minutes=int(os.getenv("AGENT_CHECKPOINT_TTL_MINUTES", "1440")),
        ))
        self._ready = False
        workflow = StateGraph(HarnessState)
        for name, handler in (("understand", understand), ("context", context), ("planner", planner),
                              ("executor", executor), ("verifier", verifier), ("synthesizer", synthesizer)):
            workflow.add_node(name, handler)
        workflow.add_edge(START, "understand")
        workflow.add_edge("understand", "context")
        workflow.add_edge("context", "planner")
        workflow.add_edge("planner", "executor")
        workflow.add_edge("executor", "verifier")
        workflow.add_conditional_edges("verifier", self._after_verifier, {"planner": "planner", "synthesizer": "synthesizer"})
        workflow.add_edge("synthesizer", END)
        self.graph = workflow.compile(checkpointer=self.checkpointer, name="oncall-evidence-harness")

    @staticmethod
    def _after_verifier(state: HarnessState) -> str:
        verification = state.get("verification", {})
        task = state.get("task", {})
        plan = state.get("plan", {})
        should_retry = (verification.get("verdict") in {"ABSTAIN", "PARTIAL"}
                        and task.get("kind") == "network_analysis"
                        and bool(plan.get("steps"))
                        and int(state.get("round", 0)) < int(state.get("max_rounds", 3)))
        return "planner" if should_retry else "synthesizer"

    async def _setup(self):
        if not self._ready:
            setup = getattr(self.checkpointer, "asetup", None)
            if setup:
                await setup()
            self._ready = True

    async def execute(self, query: str, session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> HarnessExecutionResult:
        await self._setup()
        session_id = session_id or str(uuid.uuid4())
        state = create_initial_state(query, session_id, (metadata or {}).get("run_id", str(uuid.uuid4())), metadata)
        try:
            final = await self.graph.ainvoke(state, {"configurable": {"thread_id": session_id}})
            answer = final.get("answer", {})
            verification = final.get("verification", {})
            return HarnessExecutionResult(not final.get("error"), answer.get("answer", ""), float(verification.get("score", 0.0)),
                                           final.get("trace", []), {"charts": answer.get("charts", []), "evidence": answer.get("evidence", []), "claims": answer.get("claims", []), "verdict": answer.get("verdict")}, final, final.get("error"))
        except Exception as exc:
            return HarnessExecutionResult(False, "Harness 执行失败，未生成未经验证的结论。", 0.0, [], {}, state, str(exc))

    async def astream(self, query: str, session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Compatibility stream: expose committed node trace after the run."""
        result = await self.execute(query, session_id, metadata)
        for item in result.trace:
            yield item.get("agent_name", "harness"), item


_harness: Optional[EvidenceDrivenHarness] = None


def get_harness() -> EvidenceDrivenHarness:
    global _harness
    if _harness is None:
        _harness = EvidenceDrivenHarness()
    return _harness
