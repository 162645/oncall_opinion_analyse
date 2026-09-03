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
