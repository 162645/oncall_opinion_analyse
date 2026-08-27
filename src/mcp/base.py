"""
MCP 基础类型定义
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from jsonschema import Draft202012Validator


class ToolStatus(Enum):
    """工具执行状态"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"


@dataclass
class ToolResult:
    """工具执行结果"""
    status: ToolStatus
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == ToolStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    server: str  # 所属 MCP Server
    category: str = "general"  # 分类: file, browser, memory, etc.


class BaseMCPTool:
    """
    MCP 工具基类

    所有 MCP 工具都应继承此类，实现统一的接口
    """

    def __init__(self, name: str, server: str):
        self.name = name
        self.server = server
        self._definition: Optional[ToolDefinition] = None

    @property
    def definition(self) -> ToolDefinition:
        """获取工具定义"""
        if self._definition is None:
            self._definition = self._get_definition()
        return self._definition

    def _get_definition(self) -> ToolDefinition:
        """子类实现：返回工具定义"""
        raise NotImplementedError

    async def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        raise NotImplementedError

    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        return not list(Draft202012Validator(self.definition.parameters).iter_errors(params))

    def __repr__(self) -> str:
        return f"<MCPTool:{self.name}@{self.server}>"
