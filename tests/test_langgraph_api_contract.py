import pytest

from src.api.router import langgraph


@pytest.mark.asyncio
async def test_execute_route_maps_harness_message(monkeypatch):
    class FakeHarness:
        async def execute(self, **_kwargs):
            return type("Result", (), {
                "success": True, "message": "已完成", "confidence": 0.9,
                "trace": [], "error": None,
                "state": {"task": {"kind": "network_analysis"}, "session_id": "s1"},
            })()

    monkeypatch.setattr(langgraph, "get_harness", lambda: FakeHarness())
    response = await langgraph.execute_graph(langgraph.ExecuteRequest(query="分析 UKRAINE 延迟"))
    assert response.response == "已完成"
    assert response.success is True


@pytest.mark.asyncio
async def test_tools_route_exposes_all_catalog_capabilities():
    payload = await langgraph.list_tools()
    assert {item["name"] for item in payload["tools"]} == {
        "ping.summary", "ping.trend", "ping.by_asn", "ping.by_prefix24", "ping.outliers",
        "trace.paths", "trace.path_change"
    }
