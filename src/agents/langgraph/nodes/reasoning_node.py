"""
推理节点
基于收集的信息进行推理分析
"""

from typing import Dict, Any
import logging

from ..state import AgentState
from src.llm import get_llm_gateway, TaskType

logger = logging.getLogger(__name__)


class ReasoningNode:
    """
    推理节点

    功能:
    - 整合知识库信息
    - 分析工具调用结果
    - 进行逻辑推理
    - 生成诊断结论
    """

    def __init__(self):
        self.system_prompt = """你是一位经验丰富的运维专家。

你的职责是:
1. 整合所有收集到的信息
2. 进行逻辑推理分析
3. 给出诊断结论和建议

分析框架:
1. 问题确认 - 明确问题的范围和影响
2. 信息整理 - 整合知识库、工具结果
3. 假设生成 - 基于经验生成可能的原因
4. 推理验证 - 逐一验证假设
5. 结论输出 - 给出最终结论

请用专业但易懂的语言回答，使用 Markdown 格式组织内容。
"""

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """执行推理"""
        query = self._extract_query(state)
        knowledge = state.get("knowledge", "")
        tool_results = state.get("tool_results", {})
        intent = state.get("intent", "query")

        # 构建推理提示
        prompt = self._build_prompt(query, knowledge, tool_results, intent)

        try:
            gateway = get_llm_gateway()

            # 根据意图选择任务类型
            task_type = TaskType.DIAGNOSIS if intent == "diagnosis" else TaskType.ANALYSIS

            response = await gateway.generate(
                prompt=prompt,
                task_type=task_type,
            )

            reasoning = response.content

            logger.info(f"Reasoning completed with {response.latency_ms}ms")

            return {
                "reasoning": reasoning,
                "confidence": 0.85,
                "current_step": "reasoning",
            }

        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            return {
                "reasoning": f"推理过程出错: {str(e)}",
                "error": str(e),
                "current_step": "reasoning",
            }

    def _extract_query(self, state: AgentState) -> str:
        """提取查询"""
        for msg in reversed(state.get("messages", [])):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return ""

    def _build_prompt(
        self,
        query: str,
        knowledge: str,
        tool_results: Dict[str, Any],
        intent: str,
    ) -> str:
        """构建推理提示"""
        prompt = f"## 用户问题\n\n{query}\n"

        if knowledge:
            prompt += f"\n## 知识库信息\n\n{knowledge}\n"

        if tool_results:
            prompt += "\n## 工具查询结果\n\n"
            for tool_name, result in tool_results.items():
                if result.get("success"):
                    prompt += f"### {tool_name}\n```\n{result.get('result')}\n```\n"
                else:
                    prompt += f"### {tool_name}\n查询失败: {result.get('error')}\n"

        prompt += "\n## 任务\n\n"

        if intent == "diagnosis":
            prompt += "请基于以上信息进行故障诊断分析，给出:\n1. 问题分析\n2. 可能原因\n3. 排查建议\n4. 解决方案"
        elif intent == "analysis":
            prompt += "请基于以上信息进行数据分析，给出:\n1. 数据概览\n2. 趋势分析\n3. 异常识别\n4. 行动建议"
        else:
            prompt += "请基于以上信息给出详细回答。"

        return prompt
