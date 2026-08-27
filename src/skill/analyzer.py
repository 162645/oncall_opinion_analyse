"""
流程分析器
分析用户执行流程，推荐保存为 Skill
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class ExecutionTrace:
    """执行轨迹"""
    session_id: str
    query: str
    intent: str
    steps: List[Dict[str, Any]]
    success: bool
    duration_ms: int
    user_feedback: Optional[int] = None  # 1-5 评分


@dataclass
class SkillRecommendation:
    """Skill 推荐"""
    recommended: bool
    reason: str
    suggested_name: str = ""
    suggested_description: str = ""
    suggested_workflow: List[Dict[str, Any]] = field(default_factory=list)
    suggested_trigger: Dict[str, Any] = field(default_factory=dict)
    suggested_params: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0


class FlowAnalyzer:
    """
    流程分析器

    功能:
    1. 分析执行轨迹
    2. 识别可复用模式
    3. 提取可参数化变量
    4. 生成 Skill 推荐
    """

    def __init__(self):
        # 保存最近的执行轨迹用于分析
        self._traces: List[ExecutionTrace] = []

        # 可复用模式的阈值
        self._min_steps = 2
        self._min_success_rate = 0.7
        self._min_quality_score = 0.6

    def record_trace(self, trace: ExecutionTrace):
        """记录执行轨迹"""
        self._traces.append(trace)

        # 保留最近 1000 条
        if len(self._traces) > 1000:
            self._traces = self._traces[-1000:]

    async def analyze(self, trace: ExecutionTrace) -> SkillRecommendation:
        """
        分析执行轨迹，判断是否值得保存为 Skill

        Args:
            trace: 执行轨迹

        Returns:
            SkillRecommendation
        """
        # 基本检查
        if not trace.success:
            return SkillRecommendation(
                recommended=False,
                reason="执行未成功",
            )

        if len(trace.steps) < self._min_steps:
            return SkillRecommendation(
                recommended=False,
                reason=f"步骤数量不足 ({len(trace.steps)} < {self._min_steps})",
            )

        # 计算质量分数
        quality_score = self._calculate_quality(trace)

        if quality_score < self._min_quality_score:
            return SkillRecommendation(
                recommended=False,
                reason=f"质量分数不足 ({quality_score:.2f} < {self._min_quality_score})",
            )

        # 生成推荐
        return SkillRecommendation(
            recommended=True,
            reason=f"检测到可复用的{trace.intent}流程，质量分数: {quality_score:.2f}",
            suggested_name=self._generate_name(trace),
            suggested_description=self._generate_description(trace),
            suggested_workflow=self._extract_workflow(trace),
            suggested_trigger=self._extract_trigger(trace),
            suggested_params=self._extract_params(trace),
            confidence=quality_score,
        )

    def _calculate_quality(self, trace: ExecutionTrace) -> float:
        """
        计算质量分数

        因素:
        - 成功: 基础分数
        - 步骤数量: 适中为佳
        - 用户反馈: 正面加分
        - 执行时间: 合理范围内
        - 内容完整性: 有检索、有推理
        """
        score = 0.0

        # 成功基础分
        if trace.success:
            score += 0.3

        # 步骤数量
        step_count = len(trace.steps)
        if 2 <= step_count <= 5:
            score += 0.2
        elif step_count > 5:
            score += 0.1

        # 用户反馈
        if trace.user_feedback:
            feedback_score = trace.user_feedback / 5.0
            score += 0.2 * feedback_score

        # 内容完整性
        has_retrieval = any(s.get("step_type") == "retrieval" for s in trace.steps)
        has_reasoning = any(s.get("step_type") == "reasoning" for s in trace.steps)
        has_tool = any(s.get("step_type") == "tool" for s in trace.steps)

        if has_retrieval:
            score += 0.1
        if has_reasoning:
            score += 0.15
        if has_tool:
            score += 0.05

        # 执行时间
        if trace.duration_ms < 30000:  # 30秒内
            score += 0.1
        elif trace.duration_ms < 60000:  # 1分钟内
            score += 0.05

        return min(score, 1.0)

    def _generate_name(self, trace: ExecutionTrace) -> str:
        """生成 Skill 名称"""
        query = trace.query

        # 提取关键动作
        action_keywords = {
            "诊断": ["诊断", "排查", "分析"],
            "检查": ["检查", "验证", "确认"],
            "查询": ["查询", "搜索", "获取"],
            "分析": ["分析", "统计", "趋势"],
        }

        for action, keywords in action_keywords.items():
            for kw in keywords:
                if kw in query:
                    # 提取主题
                    topic = self._extract_topic(query)
                    return f"{topic}{action}"

        # 默认名称
        return f"自定义{trace.intent}"

    def _extract_topic(self, query: str) -> str:
        """提取主题"""
        # 常见主题关键词
        topics = ["网络", "服务", "数据库", "存储", "内存", "CPU", "日志", "延迟", "错误"]

        for topic in topics:
            if topic in query:
                return topic

        return "问题"

    def _generate_description(self, trace: ExecutionTrace) -> str:
        """生成描述"""
        steps_desc = "、".join([s.get("name", s.get("step_type", "")) for s in trace.steps[:3]])
        return f"自动生成的流程: {steps_desc}"

    def _extract_workflow(self, trace: ExecutionTrace) -> List[Dict[str, Any]]:
        """提取工作流"""
        workflow = []

        for step in trace.steps:
            workflow.append({
                "step_type": step.get("step_type", "agent"),
                "name": step.get("name", step.get("step_type", "未命名")),
                "config": step.get("config", {}),
            })

        return workflow

    def _extract_trigger(self, trace: ExecutionTrace) -> Dict[str, Any]:
        """提取触发条件"""
        keywords = []

        # 从查询中提取关键词
        words = re.findall(r'[一-鿿]+|[a-zA-Z]+', trace.query)
        stopwords = {"的", "是", "在", "有", "和", "与", "或", "我", "你", "他"}

        for word in words:
            if word not in stopwords and len(word) > 1:
                keywords.append(word)

        # 限制数量
        keywords = keywords[:5]

        return {
            "keywords": keywords,
            "intent": trace.intent,
        }

    def _extract_params(self, trace: ExecutionTrace) -> List[Dict[str, Any]]:
        """提取参数"""
        params = []

        # 从查询中识别可能的参数
        # 区域
        regions = ["新加坡", "美国", "欧洲", "东京", "上海", "北京"]
        for region in regions:
            if region in trace.query:
                params.append({
                    "name": "region",
                    "type": "string",
                    "description": "目标区域",
                    "default": region,
                    "required": False,
                    "options": regions,
                })
                break

        # 服务名模式
        service_pattern = r'\b\w+(?:service|srv|app)\b'
        services = re.findall(service_pattern, trace.query, re.IGNORECASE)
        if services:
            params.append({
                "name": "service",
                "type": "string",
                "description": "目标服务",
                "default": services[0],
                "required": False,
            })

        return params

    async def find_patterns(self, min_occurrences: int = 3) -> List[Dict[str, Any]]:
        """
        发现重复出现的模式

        用于批量推荐 Skill
        """
        # 按意图分组
        by_intent: Dict[str, List[ExecutionTrace]] = {}

        for trace in self._traces:
            if trace.success:
                intent = trace.intent
                if intent not in by_intent:
                    by_intent[intent] = []
                by_intent[intent].append(trace)

        patterns = []

        for intent, traces in by_intent.items():
            if len(traces) < min_occurrences:
                continue

            # 分析步骤模式
            step_patterns = self._analyze_step_patterns(traces)

            if step_patterns:
                patterns.append({
                    "intent": intent,
                    "occurrences": len(traces),
                    "step_patterns": step_patterns,
                    "sample_queries": [t.query for t in traces[:3]],
                })

        return patterns

    def _analyze_step_patterns(self, traces: List[ExecutionTrace]) -> List[Dict[str, Any]]:
        """分析步骤模式"""
        if not traces:
            return []

        # 统计步骤类型序列
        sequences: Dict[str, int] = {}

        for trace in traces:
            seq = " -> ".join([s.get("step_type", "?") for s in trace.steps])
            sequences[seq] = sequences.get(seq, 0) + 1

        # 找最常见的序列
        if not sequences:
            return []

        most_common = max(sequences.items(), key=lambda x: x[1])

        return [{
            "sequence": most_common[0],
            "count": most_common[1],
        }]


# 全局分析器实例
_analyzer: Optional[FlowAnalyzer] = None


def get_flow_analyzer() -> FlowAnalyzer:
    """获取流程分析器实例"""
    global _analyzer
    if _analyzer is None:
        _analyzer = FlowAnalyzer()
    return _analyzer
