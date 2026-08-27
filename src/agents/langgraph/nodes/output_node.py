"""
输出节点
生成最终响应
"""

from typing import Dict, Any
import logging

from ..state import AgentState

logger = logging.getLogger(__name__)


class OutputNode:
    """
    输出节点

    功能:
    - 格式化输出
    - 生成最终响应
    - 添加置信度
    """

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """生成输出"""
        intent = state.get("intent", "query")
        reasoning = state.get("reasoning", "")
        knowledge = state.get("knowledge", "")
        tool_results = state.get("tool_results", {})
        error = state.get("error")

        # 检查是否有错误
        if error:
            response = f"❌ 处理过程中出现错误: {error}\n\n已有信息:\n{reasoning or '无'}"
            confidence = 0.3
        else:
            # 根据意图格式化输出
            response = self._format_response(intent, reasoning, knowledge, tool_results)
            confidence = state.get("confidence", 0.8)

        logger.info(f"Output generated for intent={intent}")

        return {
            "response": response,
            "confidence": confidence,
            "current_step": "output",
        }

    def _format_response(
        self,
        intent: str,
        reasoning: str,
        knowledge: str,
        tool_results: Dict[str, Any],
    ) -> str:
        """格式化响应"""
        if not reasoning:
            return "抱歉，未能生成有效的分析结果。请提供更多信息。"

        # 简单场景：直接返回推理结果
        if intent == "query":
            return reasoning

        # 复杂场景：添加结构化信息
        response = reasoning

        # 添加工具结果摘要
        if tool_results:
            response += "\n\n---\n\n📊 **数据来源**\n"
            for tool_name, result in tool_results.items():
                if result.get("success"):
                    response += f"- {tool_name}: ✅ 查询成功\n"
                else:
                    response += f"- {tool_name}: ❌ 查询失败\n"

        return response
