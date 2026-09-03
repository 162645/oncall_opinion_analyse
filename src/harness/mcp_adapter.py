"""MCP-shaped adapter for the Harness query catalog.

MCP exposes tool discovery/invocation; business rules remain in Catalog and
ToolRuntime. This adapter deliberately contains no SQL or planning logic.
"""

from typing import Any, Dict

from .catalog import CATALOG


class ExternalMCPAdapter:
    """Adapter for real MCP servers, separate from the local SQL capability."""
    def __init__(self, client):
        self.client = client

    async def initialize(self):
        await self.client.initialize()

    def list_tools(self):
        return self.client.list_tools()

    async def call_tool(self, name, arguments, *, trace_id=""):
        # MCP transports carry tool arguments; trace correlation remains a
        # Harness concern and must not leak into a remote tool schema.
        return await self.client.call_tool(name, **arguments)


class CatalogMCPAdapter:
    def __init__(self, runtime):
        self.runtime = runtime

    def list_tools(self) -> list[dict]:
        return [{"name": spec.query_id, "description": spec.description,
                 "input_schema": {"type": "object", "required": ["query_type", "region", "start_time", "end_time"]}}
                for spec in CATALOG.values()]

    async def call_tool(self, name: str, arguments: Dict[str, Any], *, trace_id: str = ""):
        return await self.runtime.execute(name, arguments, actor="mcp", trace_id=trace_id)
