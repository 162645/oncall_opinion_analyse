#!/usr/bin/env python3
"""Run reproducible local engineering benchmarks for resume claims."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.langgraph.graph_builder import AgentGraphBuilder
from src.eval.harness_benchmark import benchmark_async, percentile, to_dict
from src.mcp.client import MCPClient
from src.observability import Telemetry, TelemetryConfig
from src.runtime import (
    CheckpointConfig,
    CircuitBreakerConfig,
    PermissionLevel,
    RetryPolicy,
    ToolDefinition,
    ToolRuntime,
)
from src.skill import ReplayCase, Skill, SkillLifecycleManager, SkillStep
from src.skill.executor import SkillExecutor


class StubNode:
    def __init__(self, update):
        self.update = update
        self.calls = 0

    async def __call__(self, state):
        self.calls += 1
        return dict(self.update)


def graph(checkpoint=None, *, prefix="benchmark", confidence=0.9):
    telemetry = Telemetry(TelemetryConfig(service_name=f"harness-{prefix}"))
    kwargs = {}
    if checkpoint:
        kwargs["checkpoint_config"] = CheckpointConfig(
            backend="redis", redis_url=checkpoint, prefix=prefix, ttl_minutes=10,
        )
    return AgentGraphBuilder(
        router_node=StubNode({"intent": "diagnosis", "current_step": "router"}),
        knowledge_node=StubNode({"knowledge": "evidence", "current_step": "knowledge"}),
        tool_node=StubNode({"tool_results": {"query": "ok"}, "current_step": "tools"}),
        reasoning_node=StubNode({"reasoning": "root cause", "confidence": confidence, "current_step": "reasoning"}),
        output_node=StubNode({"response": "resolved", "current_step": "output"}),
        telemetry=telemetry,
        **kwargs,
    )


async def tool_reliability_metrics():
    baseline_counter = 0

    async def baseline_flaky():
        nonlocal baseline_counter
        baseline_counter += 1
        if baseline_counter % 3:
            raise ConnectionError("temporary")
        return True

    baseline_success = 0
    for _ in range(300):
        try:
            await baseline_flaky()
            baseline_success += 1
        except ConnectionError:
            pass

    governed_counter = 0

    async def governed_flaky():
        nonlocal governed_counter
        governed_counter += 1
        if governed_counter % 3:
            raise ConnectionError("temporary")
        return True

    runtime = ToolRuntime()
    runtime.register(ToolDefinition(
        "flaky", "flaky", {"type": "object", "properties": {}}, governed_flaky,
        retry=RetryPolicy(max_attempts=3, base_delay_ms=0, jitter_ratio=0),
    ))
    governed_success = 0
    for _ in range(300):
        governed_success += int((await runtime.execute("flaky", {})).success)

    async def slow_failure():
        await asyncio.sleep(0.005)
        raise ConnectionError("downstream unavailable")

    baseline_latencies = []
    for _ in range(100):
        started = time.perf_counter()
        try:
            await slow_failure()
        except ConnectionError:
            pass
        baseline_latencies.append((time.perf_counter() - started) * 1000)

    circuit_runtime = ToolRuntime()
    circuit_runtime.register(ToolDefinition(
        "down", "down", {"type": "object", "properties": {}}, slow_failure,
        retry=RetryPolicy(max_attempts=1),
    ), CircuitBreakerConfig(failure_threshold=5, recovery_timeout_seconds=60))
    circuit_latencies = []
    for _ in range(100):
        started = time.perf_counter()
        await circuit_runtime.execute("down", {})
        circuit_latencies.append((time.perf_counter() - started) * 1000)

    side_effect_calls = 0

    async def side_effect(value):
        nonlocal side_effect_calls
        side_effect_calls += 1
        return value

    idempotent = ToolRuntime()
    idempotent.register(ToolDefinition(
        "side", "side", {"type": "object", "properties": {"value": {"type": "integer"}}, "required": ["value"]},
        side_effect, permission=PermissionLevel.WRITE, side_effecting=True,
    ))
    for index in range(100):
        for _ in range(2):
            await idempotent.execute(
                "side", {"value": index}, granted_permission=PermissionLevel.WRITE,
                idempotency_key=f"side:{index}",
            )

    baseline_p95 = percentile(baseline_latencies, 95)
    circuit_p95 = percentile(circuit_latencies, 95)
    return {
        "transient_success_rate_before": baseline_success / 300,
        "transient_success_rate_after": governed_success / 300,
        "circuit_p95_before_ms": baseline_p95,
        "circuit_p95_after_ms": circuit_p95,
        "circuit_p95_reduction": (baseline_p95 - circuit_p95) / baseline_p95,
        "side_effect_duplicate_rate_before": 0.5,
        "side_effect_duplicate_rate_after": (side_effect_calls - 100) / 200,
        "governed_side_effect_calls": side_effect_calls,
    }


async def parallel_metric():
    async def unit():
        await asyncio.sleep(0.01)

    sequential, parallel = [], []
    for _ in range(30):
        started = time.perf_counter()
        for _ in range(4):
            await unit()
        sequential.append((time.perf_counter() - started) * 1000)
        started = time.perf_counter()
        await asyncio.gather(*(unit() for _ in range(4)))
        parallel.append((time.perf_counter() - started) * 1000)
    seq_p95, par_p95 = percentile(sequential, 95), percentile(parallel, 95)
    return {
        "sequential_p95_ms": seq_p95,
        "parallel_p95_ms": par_p95,
        "latency_reduction": (seq_p95 - par_p95) / seq_p95,
    }


async def recovery_metric(redis_url: str, cycles: int = 30):
    first, second = graph(redis_url, prefix="benchmark-recovery"), graph(redis_url, prefix="benchmark-recovery")
    recovered = 0
    for index in range(cycles):
        thread = f"recovery-{index}"
        interrupted = await first.execute("diagnose", thread, metadata={"require_human_approval": True})
        if interrupted.interrupted and (await second.resume(thread, True)).success:
            recovered += 1
    return {
        "cycles": cycles,
        "recovered": recovered,
        "recovery_success_rate": recovered / cycles,
        "tool_calls_before_restart": first.tool_node.calls,
        "tool_calls_after_restart": second.tool_node.calls,
    }


async def skill_metric(cases=100):
    skill = Skill(name="benchmark", workflow=[SkillStep("output", "render", {"template": "ok"})])
    manager = SkillLifecycleManager(SkillExecutor(), min_replay_success_rate=0.95)
    manager.register_candidate(skill)
    report = await manager.validate(skill, [ReplayCase(f"case-{i}", {}, required_steps=["render"]) for i in range(cases)])
    return {
        "cases": cases,
        "passed": report.passed,
        "success_rate": report.success_rate,
        "p95_duration_ms": report.p95_duration_ms,
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis-url", default="redis://127.0.0.1:6390/0")
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--output", default="artifacts/benchmarks/harness_metrics.json")
    args = parser.parse_args()

    client = MCPClient()
    await client.initialize()
    harness = graph(prefix="load")
    load = await benchmark_async(
        lambda index: harness.execute("diagnose", f"load-{index}"),
        requests=args.requests, concurrency=args.concurrency,
    )
    spans = harness.telemetry.finished_spans()
    executed_nodes = {span.name for span in spans if span.name.startswith("graph.")}
    expected_executed = {"graph.router", "graph.knowledge", "graph.tools", "graph.reasoning", "graph.reflection", "graph.output"}

    recovery = await recovery_metric(args.redis_url)
    tools = await tool_reliability_metrics()
    skill_replay = await skill_metric()
    parallel = await parallel_metric()
    result = {
        "environment": {"python": "3.11.15", "requests": args.requests, "concurrency": args.concurrency},
        "capabilities": {"agent_node_types": len(AgentGraphBuilder.CORE_NODES), "mcp_tools": len(client.list_tools())},
        "load": to_dict(load),
        "recovery": recovery,
        "tools": tools,
        "trace": {
            "expected_executed_nodes": len(expected_executed),
            "covered_executed_nodes": len(expected_executed & executed_nodes),
            "coverage": len(expected_executed & executed_nodes) / len(expected_executed),
            "finished_spans": len(spans),
        },
        "skill_replay": skill_replay,
        "parallel": parallel,
        "evaluation": {
            "task_success_rate": load.success_rate,
            "tool_success_rate_under_transient_fault": tools["transient_success_rate_after"],
            "recovery_success_rate": recovery["recovery_success_rate"],
            "p95_latency_ms": load.p95_ms,
            "token_cost_usd": 0.0,
            "token_cost_scope": "Synthetic Harness benchmark uses deterministic nodes and makes no LLM calls",
            "skill_regression_pass_rate": skill_replay["success_rate"],
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    await client.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
