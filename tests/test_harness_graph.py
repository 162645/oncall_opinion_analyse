import pytest

from src.harness.graph import EvidenceDrivenHarness


def test_graph_exposes_exactly_six_core_nodes():
    assert EvidenceDrivenHarness.CORE_NODES == (
        "understand", "context", "planner", "executor", "verifier", "synthesizer"
    )


@pytest.mark.asyncio
async def test_knowledge_request_completes_without_database():
    result = await EvidenceDrivenHarness().execute("你好", session_id="test-knowledge")
    assert result.success is True
    assert result.state["verification"]["verdict"] == "PASS"
    assert [item["agent_name"] for item in result.trace] == list(EvidenceDrivenHarness.CORE_NODES)


def test_diagnosis_plan_drills_down_in_stages():
    from src.harness.nodes import _steps
    task = {"kind": "network_analysis", "region": "UKRAINE", "goal": "diagnose",
        "time_range": {"start_time": "a", "end_time": "b"}}
    first = _steps(task, {"evidence": []})
    second = _steps(task, {"evidence": [
        {"evidence_id": "E1", "query_id": "ping.summary", "status": "observed"},
        {"evidence_id": "E2", "query_id": "ping.trend", "status": "observed"},
    ]})
    assert [step["query_id"] for step in first] == ["ping.summary", "ping.trend"]
    assert [step["query_id"] for step in second] == ["ping.by_asn"]

    asn = {"evidence": [
        {"evidence_id": "E1", "query_id": "ping.by_asn", "status": "observed",
         "data": {"statistics": [{"p95_rtt": 150}, {"p95_rtt": 50}]}},
    ]}
    assert [step["query_id"] for step in _steps(task, asn)] == ["ping.by_prefix24"]
    prefix = {"evidence": asn["evidence"] + [
        {"evidence_id": "E2", "query_id": "ping.by_prefix24", "status": "observed",
         "data": {"statistics": []}},
    ]}
    assert [step["query_id"] for step in _steps(task, prefix)] == []

    path_task = {**task, "wants_path_analysis": True}
    assert [step["query_id"] for step in _steps(path_task, prefix)] == ["trace.path_change"]


def test_recipe_fallback_does_not_execute_verifier_query_ids_directly():
    from src.harness.nodes import _steps
    task = {"kind": "network_analysis", "region": "UKRAINE", "goal": "diagnose",
            "time_range": {"start_time": "a", "end_time": "b"}}
    steps = _steps(task, {"evidence": []}, {"missing_evidence": [
        {"query_id": "trace.paths", "reason": "confirm path-level cause", "priority": "high"},
    ]})
    assert [step["query_id"] for step in steps] == ["ping.summary", "ping.trend"]


def test_default_budget_allows_four_stage_drilldown():
    from src.harness.state import create_initial_state
    assert create_initial_state("分析 UKRAINE 异常", "s", "r")["max_rounds"] == 4


def test_verifier_can_replan_after_round_three():
    harness = EvidenceDrivenHarness()
    assert harness._after_verifier({
        "verification": {"verdict": "REPLAN"},
        "task": {"kind": "network_analysis"},
        "plan": {"steps": [{"query_id": "trace.paths"}]},
        "round": 3, "max_rounds": 4,
    }) == "planner"


def test_only_replan_routes_back_to_planner():
    harness = EvidenceDrivenHarness()
    base = {"task": {"kind": "network_analysis"}, "plan": {"steps": [{"query_id": "ping.summary"}]},
            "round": 1, "max_rounds": 4, "budget": {"max_queries": 8, "max_tool_failures": 3,
            "deadline_seconds": 45, "started_at": 0}}
    assert harness._after_verifier({**base, "verification": {"verdict": "PARTIAL"}}) == "synthesizer"
    assert harness._after_verifier({**base, "verification": {"verdict": "ABSTAIN"}}) == "synthesizer"


def test_harness_owns_one_runtime_for_all_graph_rounds():
    harness = EvidenceDrivenHarness()
    executor_node = harness.graph.nodes["executor"]
    assert harness.runtime is not None
    assert len(harness.runtime.definitions()) >= 7


@pytest.mark.asyncio
async def test_full_four_round_drilldown_with_fake_clickhouse(monkeypatch):
    class FakeClient:
        def execute(self, sql, _params):
            if "GROUP BY ip_asn" in sql:
                return [(64500, 100, 100, 180.0, 240.0), (64501, 100, 100, 60.0, 80.0)]
            if "GROUP BY prefix24" in sql:
                return [("203.0.113.0/24", 100, 100, 180.0, 240.0)]
            if "uniqExact(ip_path_hash)" in sql:
                return [("2026-01-01 01:00:00", 2, 100, 123)]
            if "ip_path_hash" in sql:
                return [(123, 100, 8.0, 99)]
            if "toStartOfHour" in sql:
                return [("2026-01-01 01:00:00", 100, 100, 100.0, 110.0, 180.0)]
            return [(100, 100, 100.0, 110.0, 150.0, 180.0)]

    monkeypatch.setattr("src.harness.nodes.get_clickhouse_client", lambda: FakeClient())
    result = await EvidenceDrivenHarness().execute(
        "分析 UKRAINE 最近 24 小时延迟异常原因，并定位 ASN 后检查路径变化", session_id="fake-four-round"
    )
    assert result.success is True
    assert result.state["round"] == 4
    assert result.state["verification"]["verdict"] == "PARTIAL"
    assert {item["query_id"] for item in result.state["execution"]["evidence"]} >= {
        "ping.summary", "ping.trend", "ping.by_asn", "ping.by_prefix24", "trace.path_change"
    }
    evidence_ids = {item["evidence_id"] for item in result.chart_data["evidence"]}
    assert result.chart_data["claims"]
    assert all(set(claim["evidence_ids"]) <= evidence_ids for claim in result.chart_data["claims"])
