"""
追踪数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class StepType(Enum):
    """步骤类型"""
    ROUTER = "router"           # 意图路由
    RETRIEVAL = "retrieval"     # 知识检索
    TOOL_CALL = "tool_call"     # 工具调用
    REASONING = "reasoning"     # 推理思考
    DECISION = "decision"       # 决策
    ERROR = "error"             # 错误


@dataclass
class TraceStep:
    """
    单个追踪步骤

    记录 Agent 执行的每一步操作
    """
    step_id: int
    step_type: StepType
    agent_name: str
    action: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""               # 核心思考过程
    confidence: float = 0.0
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "step_id": self.step_id,
            "step_type": self.step_type.value,
            "agent_name": self.agent_name,
            "action": self.action,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ExecutionTrace:
    """
    完整执行追踪

    记录一次完整查询的执行过程
    """
    session_id: str
    query: str
    steps: List[TraceStep] = field(default_factory=list)
    final_result: Any = None
    total_duration_ms: int = 0
    status: str = "running"           # running, completed, failed
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def add_step(self, step: TraceStep) -> None:
        """添加步骤"""
        self.steps.append(step)

    def complete(self, result: Any = None, error: str = None) -> None:
        """完成追踪"""
        self.final_result = result
        self.error = error
        self.status = "completed" if not error else "failed"
        self.completed_at = datetime.now()

        # 计算总耗时
        if self.steps:
            self.total_duration_ms = sum(s.duration_ms for s in self.steps)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "query": self.query,
            "steps": [s.to_dict() for s in self.steps],
            "final_result": str(self.final_result) if self.final_result else None,
            "total_duration_ms": self.total_duration_ms,
            "status": self.status,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def get_step_count(self) -> int:
        """获取步骤数量"""
        return len(self.steps)

    def get_successful_steps(self) -> List[TraceStep]:
        """获取成功的步骤"""
        return [s for s in self.steps if s.step_type != StepType.ERROR]

    def get_failed_steps(self) -> List[TraceStep]:
        """获取失败的步骤"""
        return [s for s in self.steps if s.step_type == StepType.ERROR]
