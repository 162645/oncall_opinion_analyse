"""
意图识别路由 Agent
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import re


class Intent(Enum):
    """意图类型"""
    DIAGNOSIS = "diagnosis"           # 故障诊断
    QUERY = "query"                   # 数据查询
    KNOWLEDGE_SEARCH = "knowledge"    # 知识检索
    ANALYSIS = "analysis"             # 数据分析
    HELP = "help"                     # 帮助
    UNKNOWN = "unknown"               # 未知


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: Intent
    confidence: float
    entities: Dict[str, Any]
    suggested_agents: List[str]


class IntentClassifier:
    """意图分类器"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

        # 关键词规则
        self.intent_keywords = {
            Intent.DIAGNOSIS: [
                "诊断", "故障", "异常", "问题", "排查",
                "根因", "原因", "为什么", "怎么解决",
                "diagnose", "troubleshoot", "issue",
            ],
            Intent.QUERY: [
                "查询", "查看", "获取", "显示",
                "延迟", "流量", "指标", "数据",
                "query", "get", "show", "latency",
            ],
            Intent.KNOWLEDGE_SEARCH: [
                "搜索", "查找", "匹配", "相似",
                "案例", "SOP", "文档", "历史",
                "search", "find", "similar", "case",
            ],
            Intent.ANALYSIS: [
                "分析", "趋势", "对比", "统计",
                "报告", "汇总", "图表",
                "analyze", "trend", "compare", "report",
            ],
            Intent.HELP: [
                "帮助", "怎么用", "能做什么", "功能",
                "help", "usage", "what can you do",
            ],
        }

    def classify(self, query: str) -> IntentResult:
        """
        分类意图

        Args:
            query: 用户查询

        Returns:
            意图识别结果
        """
        query_lower = query.lower()

        # 计算各意图的分数
        scores = {}
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            scores[intent] = score

        # 选择最高分意图
        best_intent = max(scores, key=scores.get)
        confidence = scores[best_intent] / max(sum(scores.values()), 1)

        # 如果分数太低，标记为未知
        if scores[best_intent] == 0:
            best_intent = Intent.UNKNOWN
            confidence = 0.0

        # 提取实体
        entities = self._extract_entities(query)

        # 推荐 Agent
        suggested_agents = self._get_suggested_agents(best_intent, entities)

        return IntentResult(
            intent=best_intent,
            confidence=min(confidence, 1.0),
            entities=entities,
            suggested_agents=suggested_agents,
        )

    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """提取实体"""
        entities = {}

        # 提取区域
        region_patterns = [
            r"(新加坡|Singapore)[_-]?(中心|Central)?",
            r"(美国|US)[_-]?(东部|East|西部|West)?",
            r"(北京|Beijing|上海|Shanghai)",
        ]
        for pattern in region_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                entities["region"] = match.group(0)
                break

        # 提取 PSM
        psm_match = re.search(r"psm[：:\s]*([a-zA-Z0-9_.-]+)", query, re.IGNORECASE)
        if psm_match:
            entities["psm"] = psm_match.group(1)

        # 提取时间
        time_patterns = [
            (r"(\d+)\s*小时", "hours"),
            (r"(\d+)\s*分钟", "minutes"),
            (r"(\d+)\s*天", "days"),
            (r"最近\s*(\d+)", "recent"),
        ]
        for pattern, unit in time_patterns:
            match = re.search(pattern, query)
            if match:
                entities["time_range"] = {
                    "value": int(match.group(1)),
                    "unit": unit,
                }
                break

        # 提取指标
        metrics = ["延迟", "latency", "流量", "traffic", "丢包", "loss"]
        for metric in metrics:
            if metric in query.lower():
                entities["metric"] = metric
                break

        return entities

    def _get_suggested_agents(
        self,
        intent: Intent,
        entities: Dict[str, Any],
    ) -> List[str]:
        """获取推荐的 Agent"""
        agent_mapping = {
            Intent.DIAGNOSIS: ["diagnosis_agent", "knowledge_agent", "analysis_agent"],
            Intent.QUERY: ["analysis_agent"],
            Intent.KNOWLEDGE_SEARCH: ["knowledge_agent"],
            Intent.ANALYSIS: ["analysis_agent"],
            Intent.HELP: [],
            Intent.UNKNOWN: ["diagnosis_agent"],
        }
        return agent_mapping.get(intent, [])


class RouterAgent:
    """
    路由 Agent

    职责:
    1. 识别用户意图
    2. 提取实体信息
    3. 路由到合适的 Agent
    """

    def __init__(self, classifier: Optional[IntentClassifier] = None):
        self.classifier = classifier or IntentClassifier()
        self._agent_registry: Dict[str, Any] = {}

    def register_agent(self, name: str, agent: Any):
        """注册 Agent"""
        self._agent_registry[name] = agent

    def route(self, query: str) -> Tuple[IntentResult, List[Any]]:
        """
        路由查询

        Args:
            query: 用户查询

        Returns:
            (意图结果, 推荐的 Agent 列表)
        """
        # 分类意图
        intent_result = self.classifier.classify(query)

        # 获取对应的 Agent
        agents = []
        for agent_name in intent_result.suggested_agents:
            if agent_name in self._agent_registry:
                agents.append(self._agent_registry[agent_name])

        return intent_result, agents

    def get_execution_plan(
        self,
        intent: Intent,
        entities: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        生成执行计划

        根据意图和实体生成具体的执行步骤
        """
        plans = {
            Intent.DIAGNOSIS: [
                {"step": "knowledge_search", "description": "检索相似案例"},
                {"step": "data_analysis", "description": "分析网络数据"},
                {"step": "root_cause_diagnosis", "description": "诊断根因"},
                {"step": "generate_report", "description": "生成报告"},
            ],
            Intent.QUERY: [
                {"step": "parse_query", "description": "解析查询参数"},
                {"step": "execute_query", "description": "执行查询"},
                {"step": "format_result", "description": "格式化结果"},
            ],
            Intent.KNOWLEDGE_SEARCH: [
                {"step": "vector_search", "description": "向量检索"},
                {"step": "rerank", "description": "重排序"},
                {"step": "format_response", "description": "格式化响应"},
            ],
        }

        return plans.get(intent, [])
