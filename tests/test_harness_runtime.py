import asyncio
import logging

import pytest

from src.agents.langgraph.graph_builder import AgentGraphBuilder
from src.observability import Telemetry, TelemetryConfig
from src.runtime import (
    CircuitBreakerConfig,
    PermissionLevel,
    RetryPolicy,
    ToolDefinition,
    ToolErrorKind,
    ToolRuntime,
)
from src.skill import (
    ReplayCase,
    Skill,
    SkillLifecycleManager,
    SkillStatus,
    SkillStep,
)
from src.skill.executor import SkillExecutor


class StubNode:
    def __init__(self, update):
        self.update = update
        self.calls = 0

    async def __call__(self, state):
        self.calls += 1
        return self.update(state) if callable(self.update) else dict(self.update)


def build_graph(*, approval=False, confidence=0.9):
    telemetry = Telemetry(TelemetryConfig(service_name="harness-test"))
    return AgentGraphBuilder(
        router_node=StubNode({"intent": "diagnosis", "current_step": "router"}),
        knowledge_node=StubNode({"knowledge": "known issue", "current_step": "knowledge"}),
        tool_node=StubNode({"tool_results": {"read": {"ok": True}}, "current_step": "tools"}),
        reasoning_node=StubNode({"reasoning": "root cause", "confidence": confidence, "current_step": "reasoning"}),
        output_node=StubNode({"response": "resolved", "current_step": "output"}),
        telemetry=telemetry,
    )


@pytest.mark.asyncio
async def test_stategraph_routes_reflects_and_streams():
    graph = build_graph(confidence=0.4)
    result = await graph.execute("diagnose", "thread-route", metadata={"max_iterations": 2})
    assert result.success
    assert result.response == "resolved"
    assert result.state["iteration"] == 2
    events = [name async for name, _ in graph.astream("diagnose", "thread-stream")]
    assert events == ["router", "knowledge", "tools", "reasoning", "reflection", "reasoning", "reflection", "output"]


@pytest.mark.asyncio
async def test_human_interrupt_and_checkpoint_resume():
    graph = build_graph()
    first = await graph.execute("diagnose", "thread-human", metadata={"require_human_approval": True})
    assert first.interrupted
    resumed = await graph.resume("thread-human", approved=True)
    assert resumed.success
    assert resumed.response == "resolved"


@pytest.mark.asyncio
async def test_tool_runtime_validation_retry_permission_idempotency_and_circuit():
    calls = {"write": 0, "flaky": 0, "fail": 0}

    async def write(value):
        calls["write"] += 1
        return {"value": value}

    async def flaky():
        calls["flaky"] += 1
        if calls["flaky"] < 3:
            raise ConnectionError("temporary")
        return "ok"

    async def fail():
        calls["fail"] += 1
        raise ConnectionError("down")

    async def slow():
        await asyncio.sleep(0.05)
        return "late"

    runtime = ToolRuntime()
    runtime.register(ToolDefinition(
        "write", "write", {"type": "object", "properties": {"value": {"type": "integer"}}, "required": ["value"], "additionalProperties": False},
        write, PermissionLevel.WRITE, True,
    ))
    runtime.register(ToolDefinition(
        "flaky", "flaky", {"type": "object", "properties": {}, "additionalProperties": False},
        flaky, retry=RetryPolicy(max_attempts=3, base_delay_ms=0),
    ))
    runtime.register(ToolDefinition(
        "fail", "fail", {"type": "object", "properties": {}, "additionalProperties": False},
        fail, retry=RetryPolicy(max_attempts=1),
    ), CircuitBreakerConfig(failure_threshold=2, recovery_timeout_seconds=60))
    runtime.register(ToolDefinition(
        "slow", "slow", {"type": "object", "properties": {}, "additionalProperties": False},
        slow, timeout_seconds=0.001, retry=RetryPolicy(max_attempts=1),
    ))

    denied = await runtime.execute("write", {"value": 1}, granted_permission=PermissionLevel.READ, idempotency_key="write-1")
    assert denied.error_kind == ToolErrorKind.PERMISSION
    invalid = await runtime.execute("write", {"value": "bad"}, granted_permission=PermissionLevel.WRITE, idempotency_key="write-1")
    assert invalid.error_kind == ToolErrorKind.VALIDATION
    first = await runtime.execute("write", {"value": 1}, granted_permission=PermissionLevel.WRITE, idempotency_key="write-1")
    second = await runtime.execute("write", {"value": 1}, granted_permission=PermissionLevel.WRITE, idempotency_key="write-1")
    assert first.success and second.idempotency_hit and calls["write"] == 1
    retried = await runtime.execute("flaky", {})
    assert retried.success and retried.attempts == 3
    await runtime.execute("fail", {})
    await runtime.execute("fail", {})
    opened = await runtime.execute("fail", {})
    assert opened.error_kind == ToolErrorKind.CIRCUIT_OPEN and calls["fail"] == 2
    timed_out = await runtime.execute("slow", {})
    assert timed_out.error_kind == ToolErrorKind.TIMEOUT


@pytest.mark.asyncio
async def test_skill_replay_approval_publish_and_rollback():
    executor = SkillExecutor()
    manager = SkillLifecycleManager(executor, min_replay_success_rate=1.0)
    skill = Skill(name="report", workflow=[SkillStep("output", "render", {"template": "done"})])
    manager.register_candidate(skill)
    report = await manager.validate(skill, [ReplayCase("basic", {}, required_steps=["render"])])
    assert report.success_rate == 1.0 and skill.status == SkillStatus.VALIDATED
    manager.approve(skill, "reviewer")
    manager.publish(skill)
    assert skill.status == SkillStatus.PUBLISHED
    skill.version = "1.1.0"
    manager.register_candidate(skill)
    restored = manager.rollback(skill)
    assert restored.version == "1.0.0" and restored.status == SkillStatus.PUBLISHED


def test_sync_invoke_and_trace_coverage():
    graph = build_graph()
    result = graph.invoke("diagnose", "thread-sync")
    assert result.success
    span_names = {span.name for span in graph.telemetry.finished_spans()}
    expected = {"agent.run", "graph.router", "graph.knowledge", "graph.tools", "graph.reasoning", "graph.reflection", "graph.output"}
    assert expected.issubset(span_names)


def test_structured_log_bridge_exports_records():
    telemetry = Telemetry(TelemetryConfig(service_name="log-test", enable_log_bridge=True))
    logger = logging.getLogger("harness.structured")
    logger.warning("tool failed", extra={"tool_name": "query", "run_id": "run-1"})
    assert len(telemetry.finished_logs()) == 1
    logging.getLogger().removeHandler(telemetry.logging_handler)
    telemetry.shutdown()
