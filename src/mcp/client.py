"""
MCP 客户端
管理 MCP Server 连接和工具调用
"""

import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor
import threading
import inspect

from src.observability import get_telemetry
from src.runtime import (
    PermissionLevel,
    ToolDefinition as RuntimeToolDefinition,
    ToolRuntime,
)

from .base import BaseMCPTool, ToolResult, ToolDefinition, ToolStatus
from .config import MCPConfig, MCPServerConfig

if TYPE_CHECKING:
    from .tools import FileTools, BrowserTools, MemoryTools


@dataclass
class ServerConnection:
    """服务器连接状态"""
    name: str
    process: Optional[subprocess.Popen] = None
    connected: bool = False
    tools: List[str] = field(default_factory=list)
    error: Optional[str] = None


class MCPToolRegistry:
    """
    MCP 工具注册中心

    管理所有可用的 MCP 工具
    """

    def __init__(self):
        self._tools: Dict[str, BaseMCPTool] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, tool: BaseMCPTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool

        category = tool.definition.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool.name)

    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            tool = self._tools[name]
            category = tool.definition.category
            if category in self._categories:
                self._categories[category] = [
                    t for t in self._categories[category] if t != name
                ]
            del self._tools[name]
            return True
        return False

    def get_tool(self, name: str) -> Optional[BaseMCPTool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[ToolDefinition]:
        """列出工具"""
        if category:
            names = self._categories.get(category, [])
            return [self._tools[n].definition for n in names if n in self._tools]
        return [t.definition for t in self._tools.values()]

    def list_categories(self) -> List[str]:
        """列出分类"""
        return list(self._categories.keys())


class MCPClient:
    """
    MCP 客户端

    管理 MCP Server 连接和工具调用

    使用示例:
    ```python
    client = MCPClient()

    # 初始化
    await client.initialize()

    # 列出可用工具
    tools = client.list_tools()

    # 调用工具
    result = await client.call_tool("read_file", path="/tmp/test.txt")

    # 关闭
    await client.shutdown()
    ```
    """

    def __init__(self, config: Optional[MCPConfig] = None, runtime: Optional[ToolRuntime] = None):
        self.config = config or MCPConfig()
        self.registry = MCPToolRegistry()
        self._connections: Dict[str, ServerConnection] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._initialized = False
        self.runtime = runtime or ToolRuntime()
        self.telemetry = get_telemetry()
        self._request_id = 0

        # 内置工具处理器
        self._tool_handlers: Dict[str, Callable] = {}

    async def initialize(self) -> None:
        """初始化 MCP 客户端"""
        if self._initialized:
            return

        # 注册内置工具
        self._register_builtin_tools()

        # 尝试连接配置的服务器
        for name, server_config in self.config.servers.items():
            if server_config.enabled:
                try:
                    await self._connect_server(name, server_config)
                except Exception as e:
                    print(f"Warning: Failed to connect to {name}: {e}")

        self._initialized = True

    def _register_builtin_tools(self) -> None:
        """注册内置工具（不依赖外部 MCP Server）"""
        from .tools import FileTools, MemoryTools, TimeTools

        # 文件工具
        file_tools = FileTools()
        for tool_name, handler in file_tools.get_handlers().items():
            self._tool_handlers[tool_name] = handler
            self._register_runtime_tool(tool_name, handler)

        # 内存工具
        memory_tools = MemoryTools()
        for tool_name, handler in memory_tools.get_handlers().items():
            self._tool_handlers[tool_name] = handler
            self._register_runtime_tool(tool_name, handler)

        # 时间工具
        time_tools = TimeTools()
        for tool_name, handler in time_tools.get_handlers().items():
            self._tool_handlers[tool_name] = handler
            self._register_runtime_tool(tool_name, handler)

    def _register_runtime_tool(self, name: str, handler: Callable) -> None:
        """Derive a strict JSON Schema from the handler signature."""
        properties, required = {}, []
        type_map = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}
        for param_name, param in inspect.signature(handler).parameters.items():
            if param_name == "self":
                continue
            annotation = param.annotation
            json_type = type_map.get(annotation)
            schema = {"type": json_type} if json_type else {}
            properties[param_name] = schema
            if param.default is inspect.Parameter.empty:
                required.append(param_name)
        permission = PermissionLevel.READ
        if name in {"write_file", "copy_file", "create_directory", "memory_save"}:
            permission = PermissionLevel.WRITE
        if name in {"delete_file", "memory_delete", "memory_clear"}:
            permission = PermissionLevel.DANGEROUS
        self.runtime.register(RuntimeToolDefinition(
            name=name,
            description=(inspect.getdoc(handler) or name).splitlines()[0],
            parameters={
                "type": "object", "properties": properties,
                "required": required, "additionalProperties": False,
            },
            handler=handler,
            permission=permission,
            side_effecting=permission >= PermissionLevel.WRITE,
            timeout_seconds=10.0,
        ))

    async def _connect_server(
        self,
        name: str,
        config: MCPServerConfig,
    ) -> ServerConnection:
        """连接 MCP Server"""
        connection = ServerConnection(name=name)

        try:
            # 启动进程
            process = subprocess.Popen(
                [config.command] + config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**dict(subprocess.os.environ), **config.env},
            )

            connection.process = process

            # 发送初始化请求
            await self._send_request(connection, {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "oncall-opinion-analyse",
                        "version": "3.0.0",
                    },
                },
            })

            # 获取工具列表
            tools_response = await self._send_request(connection, {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            })

            if tools_response.get("result"):
                tools = tools_response["result"].get("tools", [])
                connection.tools = [t["name"] for t in tools]
                for tool in tools:
                    tool_name = tool["name"]

                    async def external_handler(_tool_name=tool_name, _connection=connection, **arguments):
                        self._request_id += 1
                        response = await self._send_request(_connection, {
                            "jsonrpc": "2.0",
                            "id": self._request_id + 100,
                            "method": "tools/call",
                            "params": {"name": _tool_name, "arguments": arguments},
                        })
                        if "error" in response:
                            raise RuntimeError(response["error"].get("message", "MCP tool error"))
                        return response.get("result", {}).get("content", [])

                    self.runtime.register(RuntimeToolDefinition(
                        name=tool_name,
                        description=tool.get("description", tool_name),
                        parameters=tool.get("inputSchema") or {
                            "type": "object", "properties": {}, "additionalProperties": True,
                        },
                        handler=external_handler,
                        permission=PermissionLevel.READ,
                        timeout_seconds=getattr(config, "timeout", 30.0),
                    ))

            connection.connected = True

        except Exception as e:
            connection.error = str(e)

        self._connections[name] = connection
        return connection

    async def _send_request(
        self,
        connection: ServerConnection,
        request: Dict[str, Any],
    ) -> Dict[str, Any]:
        """发送 JSON-RPC 请求"""
        if not connection.process:
            raise RuntimeError(f"Server {connection.name} not connected")

        loop = asyncio.get_event_loop()

        def _send():
            request_json = json.dumps(request) + "\n"
            connection.process.stdin.write(request_json.encode())
            connection.process.stdin.flush()

            response = connection.process.stdout.readline()
            return json.loads(response.decode())

        timeout = getattr(self.config, "request_timeout_seconds", 30.0)
        return await asyncio.wait_for(loop.run_in_executor(self._executor, _send), timeout=timeout)

    async def call_tool(
        self,
        name: str,
        actor: str = "anonymous",
        permission: PermissionLevel = PermissionLevel.DANGEROUS,
        idempotency_key: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """
        调用工具

        Args:
            name: 工具名称
            **kwargs: 工具参数

        Returns:
            ToolResult
        """
        # 首先检查内置工具
        if any(definition.name == name for definition in self.runtime.definitions()):
            with self.telemetry.tracer.start_as_current_span("mcp.tool.call", attributes={"tool.name": name}):
                governed = await self.runtime.execute(
                    name, kwargs, actor=actor, granted_permission=permission,
                    idempotency_key=idempotency_key,
                )
                self.telemetry.tool_counter.add(1, {"tool.name": name, "tool.success": str(governed.success).lower()})
                if governed.success:
                    if isinstance(governed.data, ToolResult):
                        return governed.data
                    return ToolResult(status=ToolStatus.SUCCESS, data=governed.data, metadata={
                        "attempts": governed.attempts,
                        "idempotency_hit": governed.idempotency_hit,
                    })
                status = ToolStatus.TIMEOUT if governed.error_kind and governed.error_kind.value == "timeout" else ToolStatus.ERROR
                return ToolResult(status=status, error=governed.error, metadata={
                    "error_kind": governed.error_kind.value if governed.error_kind else None,
                    "attempts": governed.attempts,
                })

        return ToolResult(
            status=ToolStatus.NOT_FOUND,
            error=f"Tool '{name}' not found",
        )

    def list_tools(self, server: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出可用工具"""
        tools = []

        # 内置工具
        for name in self._tool_handlers:
            tools.append({
                "name": name,
                "type": "builtin",
                "server": "internal",
            })

        # 外部 MCP 工具
        for conn_name, connection in self._connections.items():
            if server and conn_name != server:
                continue
            for tool_name in connection.tools:
                tools.append({
                    "name": tool_name,
                    "type": "mcp",
                    "server": conn_name,
                })

        return tools

    def list_servers(self) -> Dict[str, Dict[str, Any]]:
        """列出服务器状态"""
        return {
            name: {
                "connected": conn.connected,
                "tools": conn.tools,
                "error": conn.error,
            }
            for name, conn in self._connections.items()
        }

    async def shutdown(self) -> None:
        """关闭客户端"""
        for connection in self._connections.values():
            if connection.process:
                try:
                    connection.process.terminate()
                    connection.process.wait(timeout=5)
                except Exception:
                    connection.process.kill()

        self._connections.clear()
        self._executor.shutdown(wait=False)
        self._initialized = False


# 同步版本
class MCPClientSync:
    """MCP 客户端同步版本"""

    def __init__(self, config: Optional[MCPConfig] = None):
        self._async_client = MCPClient(config)

    def initialize(self) -> None:
        """初始化"""
        asyncio.run(self._async_client.initialize())

    def call_tool(self, name: str, **kwargs) -> ToolResult:
        """调用工具"""
        return asyncio.run(self._async_client.call_tool(name, **kwargs))

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出工具"""
        return self._async_client.list_tools()

    def shutdown(self) -> None:
        """关闭"""
        asyncio.run(self._async_client.shutdown())
