"""
工具基类
定义工具的接口和元数据
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


class ToolCategory(Enum):
    """工具类别"""
    NETWORK = "network"
    DATABASE = "database"
    CLOUD = "cloud"
    ANALYSIS = "analysis"
    CUSTOM = "custom"


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any] = field(default_factory=dict)
    returns: str = ""
    examples: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    deprecated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters,
            "returns": self.returns,
            "examples": self.examples,
            "tags": self.tags,
            "version": self.version,
            "deprecated": self.deprecated,
        }


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


class BaseTool(ABC):
    """
    工具基类

    所有工具必须继承此类并实现 execute 方法
    """

    def __init__(self):
        self._metadata: Optional[ToolMetadata] = None

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """返回工具元数据"""
        pass

    @abstractmethod
    async def execute(self, **params) -> ToolResult:
        """
        执行工具

        Args:
            **params: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        pass

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        required = [
            p["name"] for p in self.metadata.parameters.get("required", [])
        ]
        return all(k in params for k in required)

    def get_description_for_embedding(self) -> str:
        """生成用于语义匹配的描述"""
        m = self.metadata
        parts = [
            f"工具名称: {m.name}",
            f"功能描述: {m.description}",
            f"类别: {m.category.value}",
        ]
        if m.tags:
            parts.append(f"标签: {', '.join(m.tags)}")
        return "\n".join(parts)


def tool(
    name: str,
    description: str,
    category: ToolCategory = ToolCategory.CUSTOM,
    **kwargs
):
    """
    工具装饰器

    用于将普通函数转换为工具

    Example:
        @tool(
            name="query_latency",
            description="查询网络延迟",
            category=ToolCategory.NETWORK,
        )
        async def query_latency(region: str) -> dict:
            return {"latency": 50}
    """
    def decorator(func: Callable):
        # 创建元数据
        metadata = ToolMetadata(
            name=name,
            description=description,
            category=category,
            **kwargs
        )

        # 包装为工具类
        class FunctionTool(BaseTool):
            @property
            def metadata(self) -> ToolMetadata:
                return metadata

            async def execute(self, **params) -> ToolResult:
                try:
                    result = await func(**params)
                    return ToolResult(success=True, data=result)
                except Exception as e:
                    return ToolResult(success=False, error=str(e))

        return FunctionTool()

    return decorator
