"""Checkpointed LangGraph StateGraph Agent Harness."""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Literal, Optional

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langgraph.errors import GraphBubbleUp

from src.observability import Telemetry, get_telemetry
from src.runtime import CheckpointConfig, CheckpointerFactory

from .nodes import KnowledgeNode, OutputNode, ReasoningNode, RouterNode, ToolNode
from .state import AgentState, create_initial_state

RouteDecision = Literal["knowledge", "tools", "reasoning", "output"]


@dataclass
class GraphExecutionResult:
    success: bool
    response: str
    intent: str
    confidence: float
    steps: list
    state: Dict[str, Any]
    error: Optional[str] = None
    interrupted: bool = False
    thread_id: str = ""


class AgentGraphBuilder:
    """Single execution authority for routing, RAG, tools and reasoning."""

    CORE_NODES = (
        "router", "knowledge", "tools", "human_approval",
        "reasoning", "reflection", "output", "failure",
    )

    def __init__(
        self,
        *,
        router_node=None,
        knowledge_node=None,
        tool_node=None,
        reasoning_node=None,
        output_node=None,
        checkpoint_config: Optional[CheckpointConfig] = None,
        checkpointer=None,
        telemetry: Optional[Telemetry] = None,
        reflection_threshold: float = 0.75,
    ):
        self.router_node = router_node or RouterNode()
        self.knowledge_node = knowledge_node or KnowledgeNode()
        self.tool_node = tool_node or ToolNode()
        self.reasoning_node = reasoning_node or ReasoningNode()
        self.output_node = output_node or OutputNode()
        self.checkpoint_config = checkpoint_config or CheckpointConfig()
        self.checkpointer = checkpointer or CheckpointerFactory.create(self.checkpoint_config)
        self.telemetry = telemetry or get_telemetry()
        self.reflection_threshold = reflection_threshold
        self._checkpointer_ready = False
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("router", self._instrument("router", self.router_node))
        workflow.add_node("knowledge", self._instrument("knowledge", self.knowledge_node))
        workflow.add_node("tools", self._instrument("tools", self.tool_node))
        workflow.add_node("human_approval", self._instrument("human_approval", self._human_approval))
        workflow.add_node("reasoning", self._instrument("reasoning", self.reasoning_node))
        workflow.add_node("reflection", self._instrument("reflection", self._reflect))
        workflow.add_node("output", self._instrument("output", self.output_node))
        workflow.add_node("failure", self._instrument("failure", self._failure))
        workflow.add_edge(START, "router")
        workflow.add_conditional_edges("router", self._route_after_router, {
            "knowledge": "knowledge", "tools": "tools", "reasoning": "reasoning",
            "output": "output", "failure": "failure",
        })
        workflow.add_conditional_edges("knowledge", self._route_after_knowledge, {
            "tools": "tools", "reasoning": "reasoning", "failure": "failure",
        })
        workflow.add_conditional_edges("tools", self._route_after_tools, {
            "human_approval": "human_approval", "reasoning": "reasoning", "failure": "failure",
        })
        workflow.add_edge("human_approval", "reasoning")
        workflow.add_edge("reasoning", "reflection")
        workflow.add_conditional_edges("reflection", self._route_after_reflection, {
            "reasoning": "reasoning", "output": "output", "failure": "failure",
        })
        workflow.add_edge("output", END)
        workflow.add_edge("failure", END)
        return workflow.compile(checkpointer=self.checkpointer, name="oncall-agent-harness")

    def build(self):
        return self.graph

    def _instrument(self, node_name: str, handler):
        async def wrapped(state: AgentState):
            with self.telemetry.tracer.start_as_current_span(
                f"graph.{node_name}",
                attributes={
                    "agent.node": node_name,
                    "agent.run_id": state.get("run_id", ""),
                    "agent.iteration": state.get("iteration", 0),
                },
            ) as span:
                started = time.perf_counter()
                try:
                    update = await handler(state)
                    span.set_attribute("agent.node.success", True)
                    span.set_attribute("agent.node.duration_ms", (time.perf_counter() - started) * 1000)
                    return update
                except GraphBubbleUp:
                    raise
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_attribute("agent.node.success", False)
                    return {"error": str(exc), "current_step": node_name, "next_action": "failure"}
        return wrapped

    async def _ensure_checkpointer(self):
        if self._checkpointer_ready:
            return
        setup = getattr(self.checkpointer, "asetup", None)
        if setup:
            with self.telemetry.tracer.start_as_current_span("checkpoint.setup", attributes={
                "checkpoint.backend": self.checkpoint_config.backend,
            }):
                await setup()
        self._checkpointer_ready = True

    @staticmethod
    def _route_intent(intent: str) -> RouteDecision:
        return {
            "query": "knowledge", "diagnosis": "knowledge", "action": "tools",
            "visualization": "output", "analysis": "knowledge",
        }.get(intent, "reasoning")

    def _route_after_router(self, state: AgentState) -> str:
        return "failure" if state.get("error") else self._route_intent(state.get("intent", "query"))

    @staticmethod
    def _route_after_knowledge(state: AgentState) -> str:
        if state.get("error"):
            return "failure"
        return "tools" if state.get("intent") in {"diagnosis", "analysis"} else "reasoning"

    @staticmethod
    def _route_after_tools(state: AgentState) -> str:
        if state.get("error"):
            return "failure"
        return "human_approval" if state.get("metadata", {}).get("require_human_approval") else "reasoning"

    @staticmethod
    def _route_after_reflection(state: AgentState) -> str:
        return state.get("next_action", "output")

    async def _human_approval(self, state: AgentState) -> Dict[str, Any]:
        decision = interrupt({
            "type": "human_approval",
            "run_id": state.get("run_id"),
            "tool_results": state.get("tool_results", {}),
            "message": "Approve continuing to reasoning?",
        })
        if not bool(decision):
            return {"error": "human rejected execution", "next_action": "failure"}
        return {"current_step": "human_approval", "next_action": "reasoning"}

    async def _reflect(self, state: AgentState) -> Dict[str, Any]:
        iteration = int(state.get("iteration", 0)) + 1
        confidence = float(state.get("confidence", 0.0))
        retry = confidence < self.reflection_threshold and iteration < int(state.get("max_iterations", 2))
        return {
            "iteration": iteration,
            "current_step": "reflection",
            "next_action": "reasoning" if retry else "output",
            "metadata": {
                **state.get("metadata", {}),
                "reflection": {"accepted": not retry, "confidence": confidence, "iteration": iteration},
            },
        }

    async def _failure(self, state: AgentState) -> Dict[str, Any]:
        return {
            "response": f"Agent execution failed: {state.get('error', 'unknown error')}",
            "confidence": 0.0,
            "current_step": "failure",
        }

    @staticmethod
    def _config(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}

    async def execute(self, query: str, session_id: Optional[str] = None, *, metadata: Optional[Dict[str, Any]] = None) -> GraphExecutionResult:
        await self._ensure_checkpointer()
        thread_id = session_id or str(uuid.uuid4())
        run_id = (metadata or {}).get("run_id", str(uuid.uuid4()))
        initial = create_initial_state(query, {**(metadata or {}), "session_id": thread_id, "run_id": run_id})
        started = time.perf_counter()
        with self.telemetry.tracer.start_as_current_span("agent.run", attributes={
            "agent.thread_id": thread_id, "agent.run_id": run_id,
        }) as span:
            self.telemetry.run_counter.add(1)
            try:
                with self.telemetry.tracer.start_as_current_span("checkpoint.run", attributes={
                    "checkpoint.backend": self.checkpoint_config.backend,
                    "checkpoint.thread_id": thread_id,
                }):
                    state = await self.graph.ainvoke(initial, self._config(thread_id))
                interrupted = bool(state.get("__interrupt__"))
                result = self._result(state, thread_id, interrupted)
                span.set_attribute("agent.success", result.success)
                return result
            except Exception as exc:
                span.record_exception(exc)
                return GraphExecutionResult(False, "", "unknown", 0.0, [], initial, str(exc), thread_id=thread_id)
            finally:
                self.telemetry.latency.record((time.perf_counter() - started) * 1000)

    async def resume(self, thread_id: str, approved: bool = True) -> GraphExecutionResult:
        await self._ensure_checkpointer()
        with self.telemetry.tracer.start_as_current_span("checkpoint.resume", attributes={
            "checkpoint.backend": self.checkpoint_config.backend,
            "checkpoint.thread_id": thread_id,
        }):
            state = await self.graph.ainvoke(Command(resume=approved), self._config(thread_id))
        return self._result(state, thread_id, bool(state.get("__interrupt__")))

    async def astream(self, query: str, session_id: Optional[str] = None, *, metadata: Optional[Dict[str, Any]] = None) -> AsyncIterator[tuple[str, Dict[str, Any]]]:
        await self._ensure_checkpointer()
        thread_id = session_id or str(uuid.uuid4())
        initial = create_initial_state(query, {
            **(metadata or {}), "session_id": thread_id,
            "run_id": (metadata or {}).get("run_id", str(uuid.uuid4())),
        })
        async for event in self.graph.astream(initial, self._config(thread_id), stream_mode="updates"):
            for node_name, update in event.items():
                yield node_name, update

    def invoke(self, query: str, session_id: Optional[str] = None, **kwargs) -> GraphExecutionResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.execute(query, session_id, **kwargs))
        raise RuntimeError("invoke() cannot be used inside an event loop; use execute()")

    def stream(self, query: str, session_id: Optional[str] = None, **kwargs):
        return self.astream(query, session_id, **kwargs)

    @staticmethod
    def _result(state: Dict[str, Any], thread_id: str, interrupted: bool) -> GraphExecutionResult:
        error = state.get("error")
        return GraphExecutionResult(
            success=not error and not interrupted,
            response=state.get("response", ""),
            intent=state.get("intent", "unknown"),
            confidence=float(state.get("confidence", 0.0)),
            steps=[{"step": state.get("current_step", "")}],
            state=state,
            error=error,
            interrupted=interrupted,
            thread_id=thread_id,
        )


_graph_builder: Optional[AgentGraphBuilder] = None


def get_graph_builder() -> AgentGraphBuilder:
    global _graph_builder
    if _graph_builder is None:
        _graph_builder = AgentGraphBuilder(checkpoint_config=CheckpointConfig(
            backend=os.getenv("AGENT_CHECKPOINT_BACKEND", "memory"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            prefix=os.getenv("AGENT_CHECKPOINT_PREFIX", "oncall_agent"),
            ttl_minutes=int(os.getenv("AGENT_CHECKPOINT_TTL_MINUTES", "1440")),
        ))
    return _graph_builder
