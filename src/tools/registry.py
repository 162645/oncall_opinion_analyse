"""
工具注册中心
实现动态工具发现、注册和语义匹配
"""

import importlib
import inspect
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass

from .base import BaseTool, ToolMetadata, ToolResult, ToolCategory


@dataclass
class Tool:
    """工具包装类"""
    instance: BaseTool
    metadata: ToolMetadata
    embedding: Optional[List[float]] = None


class ToolRegistry:
    """
    工具注册中心

    功能:
    1. 动态发现 tools/plugins/ 下的工具
    2. 基于语义相似度选择工具
    3. 工具生命周期管理
    """

    def __init__(self, plugins_dir: Optional[str] = None):
        self._tools: Dict[str, Tool] = {}
        self._embedding_model = None
        self.plugins_dir = plugins_dir or str(
            Path(__file__).parent / "plugins"
        )

    def register(
        self,
        tool: BaseTool,
        embedding: Optional[List[float]] = None,
    ) -> None:
        """
        注册工具

        Args:
            tool: 工具实例
            embedding: 工具描述的向量（可选，用于语义匹配）
        """
        metadata = tool.metadata

        if metadata.deprecated:
            return  # 跳过已废弃的工具

        self._tools[metadata.name] = Tool(
            instance=tool,
            metadata=metadata,
            embedding=embedding,
        )

    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        tool = self._tools.get(name)
        return tool.instance if tool else None

    def list_all(self) -> List[ToolMetadata]:
        """列出所有工具"""
        return [t.metadata for t in self._tools.values()]

    def list_by_category(self, category: ToolCategory) -> List[ToolMetadata]:
        """按类别列出工具"""
        return [
            t.metadata for t in self._tools.values()
            if t.metadata.category == category
        ]

    def discover_tools(self) -> int:
        """
        自动发现并注册插件

        扫描 tools/plugins/ 目录，加载所有工具

        Returns:
            发现的工具数量
        """
        count = 0
        plugins_path = Path(self.plugins_dir)

        if not plugins_path.exists():
            return 0

        # 遍历插件目录
        for category_dir in plugins_path.iterdir():
            if not category_dir.is_dir():
                continue

            # 遍历类别下的模块（包括 __init__.py）
            for module_file in category_dir.glob("*.py"):
                # 跳过 __pycache__ 等特殊文件
                if module_file.name.startswith("__pycache__"):
                    continue

                # 动态导入模块
                module_name = f"src.tools.plugins.{category_dir.name}.{module_file.stem}"

                # 对于 __init__.py，使用包名导入
                if module_file.name == "__init__.py":
                    module_name = f"src.tools.plugins.{category_dir.name}"

                try:
                    module = importlib.import_module(module_name)

                    # 查找模块中的工具类
                    for name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj) and
                            issubclass(obj, BaseTool) and
                            obj is not BaseTool
                        ):
                            try:
                                tool_instance = obj()
                                self.register(tool_instance)
                                count += 1
                            except Exception:
                                pass  # 跳过初始化失败的工具

                except ImportError:
                    pass  # 跳过导入失败的模块

        # 同时加载 plugins 目录下直接的 .py 文件
        for module_file in plugins_path.glob("*.py"):
            if module_file.name.startswith("_"):
                continue

            module_name = f"src.tools.plugins.{module_file.stem}"

            try:
                module = importlib.import_module(module_name)

                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj) and
                        issubclass(obj, BaseTool) and
                        obj is not BaseTool
                    ):
                        try:
                            tool_instance = obj()
                            self.register(tool_instance)
                            count += 1
                        except Exception:
                            pass

            except ImportError:
                pass

        return count

    def select_tools(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5,
    ) -> List[BaseTool]:
        """
        基于语义相似度选择相关工具

        Args:
            query: 用户查询
            top_k: 返回数量
            threshold: 相似度阈值

        Returns:
            相关工具列表
        """
        if not self._embedding_model:
            # 如果没有嵌入模型，返回所有工具
            return [t.instance for t in list(self._tools.values())[:top_k]]

        # 计算查询向量
        query_embedding = self._embedding_model.embed_single(query)

        # 计算相似度
        scored_tools = []
        for tool in self._tools.values():
            if tool.embedding is None:
                # 懒加载计算工具描述向量
                tool.embedding = self._embedding_model.embed_single(
                    tool.instance.get_description_for_embedding()
                )

            similarity = self._compute_similarity(query_embedding, tool.embedding)

            if similarity >= threshold:
                scored_tools.append((similarity, tool.instance))

        # 排序并返回 top_k
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored_tools[:top_k]]

    def _compute_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """计算余弦相似度"""
        import numpy as np

        v1 = np.array(vec1)
        v2 = np.array(vec2)

        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot / (norm1 * norm2))

    def set_embedding_model(self, model):
        """设置嵌入模型（用于语义匹配）"""
        self._embedding_model = model

    async def execute(
        self,
        name: str,
        **params,
    ) -> ToolResult:
        """
        执行工具

        Args:
            name: 工具名称
            **params: 工具参数

        Returns:
            执行结果
        """
        tool = self.get(name)

        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not found",
            )

        if not tool.validate_params(params):
            return ToolResult(
                success=False,
                error=f"Invalid parameters for tool '{name}'",
            )

        return await tool.execute(**params)

    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工具的 JSON Schema（用于 LLM 函数调用）"""
        tool = self._tools.get(name)
        if not tool:
            return None

        m = tool.metadata
        return {
            "name": m.name,
            "description": m.description,
            "parameters": m.parameters,
        }

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具的 JSON Schema"""
        return [
            self.get_tool_schema(name)
            for name in self._tools
            if self.get_tool_schema(name)
        ]


# 全局单例
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """获取全局工具注册中心"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _registry.discover_tools()
    return _registry
