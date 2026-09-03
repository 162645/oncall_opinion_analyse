"""
Agent 状态定义
定义 LangGraph 状态机的状态结构
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from dataclasses import dataclass, field
import operator


class AgentState(TypedDict):
    """
    Agent 状态

    用于 LangGraph 状态机的状态定义
    """
    # 对话历史
    messages: Annotated[List[Dict[str, str]], operator.add]

    # 识别的意图
    intent: str

    # 知识检索结果
    knowledge: str

    # 工具调用结果
    tool_results: Dict[str, Any]

    # 推理过程
    reasoning: str

    # 最终响应
    response: str

    # 置信度
    confidence: float

    # 当前步骤
    current_step: str

    # 错误信息
    error: Optional[str]

    # 元数据
    metadata: Dict[str, Any]

    # Runtime control and recovery fields
    run_id: str
    iteration: int
    max_iterations: int
    next_action: str
    completed_tools: Dict[str, Any]
    recovery_count: int
    state_version: int


@dataclass
class Message:
    """消息结构"""
    role: str  # system, user, assistant, tool
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


@dataclass
class ToolResult:
    """工具调用结果"""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: int = 0


def create_initial_state(query: str, metadata: Optional[Dict[str, Any]] = None) -> AgentState:
    """创建初始状态"""
    return AgentState(
        messages=[{"role": "user", "content": query}],
        intent="",
        knowledge="",
        tool_results={},
        reasoning="",
        response="",
        confidence=0.0,
        current_step="start",
        error=None,
        metadata=metadata or {},
        run_id=(metadata or {}).get("run_id", ""),
        iteration=0,
        max_iterations=int((metadata or {}).get("max_iterations", 2)),
        next_action="route",
        completed_tools={},
        recovery_count=0,
        state_version=1,
    )
