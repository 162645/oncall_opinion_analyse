import pytest

from src.harness.mcp_adapter import CatalogMCPAdapter
from src.harness.nodes import _catalog_runtime


def test_mcp_adapter_only_exposes_catalog_tools():
    tools = CatalogMCPAdapter(_catalog_runtime()).list_tools()
    assert {item["name"] for item in tools} == {
        "ping.summary", "ping.trend", "ping.by_asn", "ping.by_prefix24", "ping.outliers",
        "trace.paths", "trace.path_change"
    }


@pytest.mark.asyncio
async def test_mcp_adapter_uses_runtime_validation():
    adapter = CatalogMCPAdapter(_catalog_runtime())
    result = await adapter.call_tool("ping.summary", {"region": "bad;drop", "query_type": "ping_stats",
                                                        "start_time": "a", "end_time": "b"})
    assert result.success is False
    assert result.error_kind.value == "permanent"
