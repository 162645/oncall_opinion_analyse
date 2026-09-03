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
    assert [step["query_id"] for step in _steps(task, prefix)] == ["trace.paths"]
