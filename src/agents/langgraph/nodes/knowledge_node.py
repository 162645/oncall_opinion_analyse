"""
知识检索节点
从知识库检索相关信息
"""

from typing import Dict, Any
import logging

from ..state import AgentState
from src.knowledge.service import get_knowledge_service

logger = logging.getLogger(__name__)


class KnowledgeNode:
    """
    知识检索节点

    功能:
    - 从知识库检索相关信息
    - 向量检索 + 关键词检索
    - 结果融合和排序
    """

    def __init__(self, top_k: int = 5):
        self.top_k = top_k

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """执行知识检索"""
        # 获取查询
        query = self._extract_query(state)

        if not query:
            return {
                "knowledge": "",
                "current_step": "knowledge",
            }

        try:
            # 调用知识库服务
            service = get_knowledge_service()
            result = await service.search(query, top_k=self.top_k)

            # 格式化结果
            knowledge = self._format_results(result.results)

            logger.info(f"Knowledge: found {len(result.results)} results for query")

            return {
                "knowledge": knowledge,
                "current_step": "knowledge",
            }

        except Exception as e:
            logger.error(f"Knowledge retrieval failed: {e}")
            return {
                "knowledge": "",
                "error": str(e),
                "current_step": "knowledge",
            }

    def _extract_query(self, state: AgentState) -> str:
        """提取查询"""
        for msg in reversed(state.get("messages", [])):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return ""

    def _format_results(self, results: list) -> str:
        """格式化检索结果"""
        if not results:
            return ""

        formatted = []
        for i, r in enumerate(results[:3], 1):
            title = r.metadata.get("doc_title", "知识库")
            content = r.content[:500]  # 限制长度
            formatted.append(f"**[{i}] {title}**\n{content}")

        return "\n\n---\n\n".join(formatted)
