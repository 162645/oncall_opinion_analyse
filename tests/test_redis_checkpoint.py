import pytest
from redis.asyncio import Redis

from src.agents.langgraph.graph_builder import AgentGraphBuilder
from src.observability import Telemetry, TelemetryConfig
from src.runtime import CheckpointConfig, RedisExecutionLedger, ToolDefinition, ToolRuntime, PermissionLevel


class StubNode:
    def __init__(self, update):
        self.update = update
        self.calls = 0

    async def __call__(self, state):
        self.calls += 1
        return dict(self.update)


def redis_graph(prefix):
    return AgentGraphBuilder(
        router_node=StubNode({"intent": "action", "current_step": "router"}),
        knowledge_node=StubNode({"knowledge": "", "current_step": "knowledge"}),
        tool_node=StubNode({"tool_results": {"change": "committed"}, "current_step": "tools"}),
        reasoning_node=StubNode({"reasoning": "done", "confidence": 0.9, "current_step": "reasoning"}),
        output_node=StubNode({"response": "done", "current_step": "output"}),
        checkpoint_config=CheckpointConfig(
            backend="redis",
            redis_url="redis://127.0.0.1:6390/0",
            prefix=prefix,
            ttl_minutes=10,
        ),
        telemetry=Telemetry(TelemetryConfig(service_name=f"test-{prefix}")),
    )


@pytest.mark.asyncio
async def test_redis_checkpoint_survives_builder_restart():
    first_process = redis_graph("restart-test")
    interrupted = await first_process.execute(
        "change config", "redis-recovery-thread",
        metadata={"require_human_approval": True},
    )
    assert interrupted.interrupted
    assert first_process.tool_node.calls == 1

    second_process = redis_graph("restart-test")
    resumed = await second_process.resume("redis-recovery-thread", approved=True)
    assert resumed.success and resumed.response == "done"
    assert second_process.tool_node.calls == 0


@pytest.mark.asyncio
async def test_redis_side_effect_ledger_prevents_duplicate_execution():
    redis = Redis.from_url("redis://127.0.0.1:6390/0")
    await redis.flushdb()
    calls = 0

    async def side_effect(value):
        nonlocal calls
        calls += 1
        return {"committed": value}

    runtime = ToolRuntime(idempotency_store=RedisExecutionLedger(redis, "ledger-test"))
    runtime.register(ToolDefinition(
        "side_effect", "side effect",
        {"type": "object", "properties": {"value": {"type": "integer"}}, "required": ["value"]},
        side_effect, permission=PermissionLevel.WRITE, side_effecting=True,
    ))
    first = await runtime.execute(
        "side_effect", {"value": 7}, granted_permission=PermissionLevel.WRITE,
        idempotency_key="run:node:side-effect:7",
    )
    second = await runtime.execute(
        "side_effect", {"value": 7}, granted_permission=PermissionLevel.WRITE,
        idempotency_key="run:node:side-effect:7",
    )
    assert first.success and second.success and second.idempotency_hit
    assert calls == 1
    await redis.aclose()
