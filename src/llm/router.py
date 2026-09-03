"""
LLM 智能路由器
根据任务类型和内容自动选择最优模型
"""

from enum import Enum
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
import re


class TaskType(Enum):
    """任务类型"""
    SIMPLE = "simple"           # 简单查询
    COMPLEX = "complex"         # 复杂推理
    CODE = "code"               # 代码生成
    ANALYSIS = "analysis"       # 数据分析
    DIAGNOSIS = "diagnosis"     # 故障诊断
    CHAT = "chat"               # 普通对话
    TRANSLATION = "translation" # 翻译
    SUMMARY = "summary"         # 摘要生成


@dataclass
class ModelConfig:
    """模型配置"""
    provider: str
    model: str
    max_tokens: int = 4096
    temperature: float = 0.7
    cost_per_1k_tokens: float = 0.0
    latency_tier: str = "medium"  # low, medium, high


# 模型配置表
MODEL_REGISTRY: Dict[str, ModelConfig] = {
    # DeepSeek 生产模型
    "deepseek-chat": ModelConfig("deepseek", "deepseek-chat", 8192, 0.7, 0.0, "low"),
    "deepseek-reasoner": ModelConfig("deepseek", "deepseek-reasoner", 65536, 0.7, 0.0, "medium"),

    # OpenAI 模型
    "gpt-4": ModelConfig("openai", "gpt-4", 8192, 0.7, 0.03, "medium"),
    "gpt-4-turbo": ModelConfig("openai", "gpt-4-turbo-preview", 128000, 0.7, 0.01, "medium"),
    "gpt-4o": ModelConfig("openai", "gpt-4o", 128000, 0.7, 0.005, "low"),
    "gpt-3.5-turbo": ModelConfig("openai", "gpt-3.5-turbo", 16384, 0.7, 0.0005, "low"),

    # Claude 模型
    "claude-3-opus": ModelConfig("claude", "claude-3-opus-20240229", 200000, 0.7, 0.015, "high"),
    "claude-3-sonnet": ModelConfig("claude", "claude-3-sonnet-20240229", 200000, 0.7, 0.003, "medium"),
    "claude-3-haiku": ModelConfig("claude", "claude-3-haiku-20240307", 200000, 0.7, 0.00025, "low"),

    # 本地模型
    "local-qwen": ModelConfig("local", "qwen-72b", 32768, 0.7, 0.0, "high"),
    "local-llama": ModelConfig("local", "llama-3-70b", 8192, 0.7, 0.0, "high"),
}


class LLMRouter:
    """
    智能路由器

    功能:
    1. 根据任务类型选择模型
    2. 根据内容特征选择模型
    3. 考虑成本和延迟
    4. 支持自定义路由策略
    """

    def __init__(self):
        self.model_registry = MODEL_REGISTRY
        self._task_keywords = self._build_task_keywords()

    def _build_task_keywords(self) -> Dict[TaskType, list]:
        """构建任务关键词映射"""
        return {
            TaskType.CODE: [
                "代码", "code", "函数", "function", "类", "class",
                "实现", "implement", "编写", "write", "debug", "调试",
                "重构", "refactor", "优化", "optimize",
            ],
            TaskType.DIAGNOSIS: [
                "诊断", "diagnose", "故障", "failure", "异常", "error",
                "排查", "troubleshoot", "根因", "root cause", "报警", "alert",
            ],
            TaskType.ANALYSIS: [
                "分析", "analyze", "统计", "statistics", "趋势", "trend",
                "对比", "compare", "报表", "report", "指标", "metric",
            ],
            TaskType.SUMMARY: [
                "摘要", "summary", "总结", "summarize", "概括", "brief",
                "要点", "key points",
            ],
            TaskType.TRANSLATION: [
                "翻译", "translate", "translate to", "译为",
            ],
            TaskType.SIMPLE: [
                "是什么", "什么是", "怎么", "如何", "how to", "what is",
            ],
            TaskType.COMPLEX: [
                "详细分析", "深入分析", "综合", "全面", "评估", "evaluate",
                "设计", "design", "规划", "plan",
            ],
        }

    def classify_task(self, prompt: str) -> TaskType:
        """分类任务类型"""
        prompt_lower = prompt.lower()

        # 计算各类型的匹配分数
        scores: Dict[TaskType, int] = {}

        for task_type, keywords in self._task_keywords.items():
            score = 0
            for kw in keywords:
                if kw in prompt_lower:
                    score += 1
            scores[task_type] = score

        # 找最高分
        max_score = max(scores.values())
        if max_score == 0:
            return TaskType.CHAT

        # 返回最高分的类型
        for task_type, score in scores.items():
            if score == max_score:
                return task_type

        return TaskType.CHAT

    def select(
        self,
        prompt: str,
        task_type: Optional[TaskType] = None,
        prefer_provider: Optional[str] = None,
        max_latency_tier: str = "high",
    ) -> Tuple[str, str]:
        """
        选择最优的 provider 和 model

        Args:
            prompt: 输入提示
            task_type: 任务类型（可选，自动推断）
            prefer_provider: 偏好的提供商
            max_latency_tier: 最大延迟等级

        Returns:
            (provider, model_name)
        """
        # 自动分类任务
        if task_type is None:
            task_type = self.classify_task(prompt)

        # 根据任务类型选择模型
        model = self._select_by_task(task_type, prefer_provider, max_latency_tier)

        config = self.model_registry.get(model)
        if config:
            return config.provider, config.model

        # 默认使用 DeepSeek
        return "deepseek", "deepseek-chat"

    def _select_by_task(
        self,
        task_type: TaskType,
        prefer_provider: Optional[str],
        max_latency_tier: str,
    ) -> str:
        """根据任务类型选择模型"""
        latency_order = {"low": 0, "medium": 1, "high": 2}
        max_latency = latency_order.get(max_latency_tier, 2)

        # 任务类型到模型的映射，默认统一走 DeepSeek，避免旧网关网络超时。
        task_model_map = {
            TaskType.CODE: ["deepseek-reasoner", "deepseek-chat"],
            TaskType.DIAGNOSIS: ["deepseek-reasoner", "deepseek-chat"],
            TaskType.ANALYSIS: ["deepseek-chat", "deepseek-reasoner"],
            TaskType.SUMMARY: ["deepseek-chat", "deepseek-reasoner"],
            TaskType.TRANSLATION: ["deepseek-chat"],
            TaskType.SIMPLE: ["deepseek-chat"],
            TaskType.COMPLEX: ["deepseek-reasoner", "deepseek-chat"],
            TaskType.CHAT: ["deepseek-chat", "deepseek-reasoner"],
        }

        candidates = task_model_map.get(task_type, ["gpt-4o"])

        # 按偏好和延迟筛选
        for model_name in candidates:
            config = self.model_registry.get(model_name)
            if not config:
                continue

            # 检查延迟
            if latency_order.get(config.latency_tier, 2) > max_latency:
                continue

            # 检查偏好
            if prefer_provider and config.provider != prefer_provider:
                # 如果有偏好但不匹配，继续检查下一个
                pass

            return model_name

        # 如果都不过滤，返回第一个候选
        return candidates[0]

    def is_chinese_heavy(self, text: str) -> bool:
        """判断是否中文为主"""
        if not text:
            return False

        chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
        return chinese_chars / max(len(text), 1) > 0.3

    def estimate_complexity(self, prompt: str) -> float:
        """估算任务复杂度 (0-1)"""
        complexity = 0.0

        # 长度因素
        if len(prompt) > 1000:
            complexity += 0.2
        elif len(prompt) > 500:
            complexity += 0.1

        # 关键词因素
        complex_keywords = [
            "详细", "深入", "全面", "综合", "分析", "评估",
            "设计", "规划", "对比", "优化",
        ]
        for kw in complex_keywords:
            if kw in prompt:
                complexity += 0.1

        # 任务类型因素
        task_type = self.classify_task(prompt)
        if task_type in [TaskType.DIAGNOSIS, TaskType.COMPLEX, TaskType.CODE]:
            complexity += 0.3

        return min(complexity, 1.0)

    def get_model_info(self, model_name: str) -> Optional[ModelConfig]:
        """获取模型信息"""
        return self.model_registry.get(model_name)
