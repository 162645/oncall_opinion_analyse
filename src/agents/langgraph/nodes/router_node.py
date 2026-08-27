"""
路由节点
识别用户意图并决定下一步
"""

from typing import Dict, Any
import logging

from ..state import AgentState
from src.llm import get_llm_gateway, TaskType

logger = logging.getLogger(__name__)


class RouterNode:
    """
    路由节点

    功能:
    - 分析用户问题
    - 识别意图类型
    - 决定下一步路由
    """

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """执行路由"""
        # 获取最后一条用户消息
        query = ""
        for msg in reversed(state.get("messages", [])):
            if msg.get("role") == "user":
                query = msg.get("content", "")
                break

        if not query:
            return {"intent": "unknown", "current_step": "router"}

        # 使用 LLM 进行意图识别
        intent = await self._classify_intent(query)

        logger.info(f"Router: query='{query[:50]}...' -> intent={intent}")

        return {
            "intent": intent,
            "current_step": "router",
        }

    async def _classify_intent(self, query: str) -> str:
        """分类意图"""
        # 先用规则快速匹配
        intent = self._rule_based_classify(query)
        if intent != "unknown":
            return intent

        # 使用 LLM 进行更精确的分类
        try:
            gateway = get_llm_gateway()

            prompt = f"""分析用户问题，识别意图类型:

用户问题: {query}

意图类型:
- query: 简单知识查询（是什么、怎么用）
- diagnosis: 故障诊断分析（异常、故障、排查）
- action: 执行运维操作（重启、修改配置）
- visualization: 数据可视化（画图、趋势、对比）
- analysis: 数据分析（统计、分析、报告）

只输出意图类型名称（单个单词）。"""

            response = await gateway.generate(prompt, task_type=TaskType.SIMPLE)
            intent = response.content.strip().lower()

            # 验证意图类型
            valid_intents = ["query", "diagnosis", "action", "visualization", "analysis"]
            if intent in valid_intents:
                return intent

        except Exception as e:
            logger.error(f"LLM intent classification failed: {e}")

        return "query"

    def _rule_based_classify(self, query: str) -> str:
        """基于规则的意图分类"""
        query_lower = query.lower()

        # 可视化关键词
        viz_keywords = ["趋势", "图表", "对比", "画", "显示", "生成图表", "可视化"]
        if any(kw in query for kw in viz_keywords):
            return "visualization"

        # 诊断关键词
        diagnosis_keywords = ["故障", "异常", "问题", "排查", "诊断", "为什么", "错误", "报警"]
        if any(kw in query for kw in diagnosis_keywords):
            return "diagnosis"

        # 操作关键词
        action_keywords = ["重启", "修改", "执行", "运行", "部署", "发布", "回滚"]
        if any(kw in query for kw in action_keywords):
            return "action"

        # 分析关键词
        analysis_keywords = ["分析", "统计", "报告", "汇总", "对比"]
        if any(kw in query for kw in analysis_keywords):
            return "analysis"

        return "unknown"
