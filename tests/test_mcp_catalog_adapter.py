import pytest

from src.harness.mcp_adapter import CatalogMCPAdapter, ExternalMCPAdapter
from src.harness.nodes import _catalog_runtime


def test_mcp_adapter_only_exposes_catalog_tools():
    tools = CatalogMCPAdapter(_catalog_runtime()).list_tools()
    assert {item["name"] for item in tools} == {
        "ping.summary", "ping.trend", "ping.by_asn", "ping.by_prefix24", "ping.outliers", "ping.compare_window",
        "trace.paths", "trace.path_change"
    }


@pytest.mark.asyncio
async def test_mcp_adapter_uses_runtime_validation():
    adapter = CatalogMCPAdapter(_catalog_runtime())
    result = await adapter.call_tool("ping.summary", {"region": "bad;drop", "query_type": "ping_stats",
                                                        "start_time": "a", "end_time": "b"})
    assert result.success is False
    assert result.error_kind.value == "permanent"


@pytest.mark.asyncio
async def test_external_mcp_adapter_does_not_leak_trace_id_into_tool_args():
    class Client:
        async def call_tool(self, name, **kwargs):
            return name, kwargs

    result = await ExternalMCPAdapter(Client()).call_tool("remote.search", {"q": "rtt"}, trace_id="run-1")
    assert result == ("remote.search", {"q": "rtt"})
