"""
ReAct Agent 类型定义
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ReActState(Enum):
    """ReAct 状态"""
    THINKING = "thinking"      # 思考中
    ACTING = "acting"          # 行动中
    OBSERVING = "observing"    # 观察结果
    FINISHED = "finished"      # 完成
    FAILED = "failed"          # 失败


@dataclass
class ThoughtAction:
    """思考和行动"""
    thought: str                           # 思考内容
    action: Optional[str] = None           # 行动名称
    action_input: Optional[Dict] = None    # 行动参数
    observation: Optional[str] = None      # 观察结果


@dataclass
class ReActStep:
    """ReAct 单步"""
    step_id: int
    state: ReActState
    thought: Optional[str] = None
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "state": self.state.value,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ReActTrace:
    """ReAct 执行追踪"""
    query: str
    steps: List[ReActStep] = field(default_factory=list)
    final_answer: Optional[str] = None
    success: bool = False
    total_steps: int = 0
    total_duration_ms: int = 0

    def add_step(self, step: ReActStep) -> None:
        self.steps.append(step)
        self.total_steps = len(self.steps)
        self.total_duration_ms += step.duration_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "steps": [s.to_dict() for s in self.steps],
            "final_answer": self.final_answer,
            "success": self.success,
            "total_steps": self.total_steps,
            "total_duration_ms": self.total_duration_ms,
        }
