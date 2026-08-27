"""
Self-Reflection Agent 类型定义
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ReflectionQuality(Enum):
    """反思质量评估"""
    EXCELLENT = "excellent"    # 优秀
    GOOD = "good"             # 良好
    ACCEPTABLE = "acceptable" # 可接受
    POOR = "poor"            # 较差
    FAILED = "failed"        # 失败


@dataclass
class Improvement:
    """改进建议"""
    aspect: str                           # 改进方面
    current: str                          # 当前状态
    suggestion: str                       # 改进建议
    priority: int = 1                     # 优先级 1-5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "aspect": self.aspect,
            "current": self.current,
            "suggestion": self.suggestion,
            "priority": self.priority,
        }


@dataclass
class ReflectionResult:
    """反思结果"""
    quality: ReflectionQuality
    score: float                          # 0-1 评分
    strengths: List[str] = field(default_factory=list)      # 优点
    weaknesses: List[str] = field(default_factory=list)     # 不足
    improvements: List[Improvement] = field(default_factory=list)  # 改进建议
    should_retry: bool = False            # 是否需要重试
    retry_strategy: Optional[str] = None  # 重试策略
    feedback: Optional[str] = None        # 综合反馈

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quality": self.quality.value,
            "score": self.score,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "improvements": [i.to_dict() for i in self.improvements],
            "should_retry": self.should_retry,
            "retry_strategy": self.retry_strategy,
            "feedback": self.feedback,
        }


@dataclass
class ReflectionStep:
    """反思步骤"""
    step_id: int
    aspect: str                           # 评估方面
    evaluation: str                       # 评估内容
    score: float                          # 分数
    issues: List[str] = field(default_factory=list)  # 问题列表

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "aspect": self.aspect,
            "evaluation": self.evaluation,
            "score": self.score,
            "issues": self.issues,
        }
