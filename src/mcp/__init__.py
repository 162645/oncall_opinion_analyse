"""
MCP (Model Context Protocol) 集成模块
提供统一的 MCP 工具管理和调用接口
"""

from .client import MCPClient, MCPToolRegistry
from .config import MCPConfig, load_mcp_config
from .base import BaseMCPTool, ToolResult

__all__ = [
    "MCPClient",
    "MCPToolRegistry",
    "MCPConfig",
    "load_mcp_config",
    "BaseMCPTool",
    "ToolResult",
]
