"""
追踪收集器
"""

import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

from .models import TraceStep, ExecutionTrace, StepType


class TraceCollector:
    """
    追踪收集器

    用于收集 Agent 执行过程中的追踪信息

    使用方式:
    ```python
    collector = TraceCollector()
    collector.start_trace("session-001", "查询延迟")

    with collector.trace_step(
        step_type=StepType.TOOL_CALL,
        agent_name="AnalysisAgent",
        action="query_latency",
    ) as step:
        result = query_latency()
        step.output_data = result
        step.reasoning = "查询完成"

    trace = collector.end_trace()
    ```
    """

    def __init__(self):
        self._current_trace: Optional[ExecutionTrace] = None
        self._step_counter = 0
        self._step_stack: list = []  # 支持嵌套步骤

    def start_trace(self, session_id: str, query: str) -> ExecutionTrace:
        """
        开始追踪

        Args:
            session_id: 会话 ID
            query: 用户查询

        Returns:
            新创建的追踪对象
        """
        self._current_trace = ExecutionTrace(
            session_id=session_id,
            query=query,
        )
        self._step_counter = 0
        self._step_stack = []
        return self._current_trace

    @contextmanager
    def trace_step(
        self,
        step_type: StepType,
        agent_name: str,
        action: str,
        input_data: Dict = None,
    ):
        """
        追踪单个步骤（上下文管理器）

        Args:
            step_type: 步骤类型
            agent_name: Agent 名称
            action: 动作描述
            input_data: 输入数据

        Yields:
            TraceStep: 步骤对象，调用者可以填充 output_data 和 reasoning

        Example:
            with collector.trace_step(
                step_type=StepType.TOOL_CALL,
                agent_name="AnalysisAgent",
                action="query_latency",
                input_data={"region": "Singapore"},
            ) as step:
                result = query_latency("Singapore")
                step.output_data = result
                step.reasoning = "查询完成，延迟正常"
        """
        start_time = time.time()
        step_id = self._step_counter
        self._step_counter += 1

        step = TraceStep(
            step_id=step_id,
            step_type=step_type,
            agent_name=agent_name,
            action=action,
            input_data=input_data or {},
        )

        # 支持嵌套
        self._step_stack.append(step)

        try:
            yield step
        except Exception as e:
            # 发生错误时记录
            step.step_type = StepType.ERROR
            step.output_data = {"error": str(e)}
            step.reasoning = f"执行出错: {str(e)}"
            raise
        finally:
            # 计算耗时
            step.duration_ms = int((time.time() - start_time) * 1000)

            # 添加到追踪
            if self._current_trace:
                self._current_trace.add_step(step)

            # 从栈中移除
            if self._step_stack:
                self._step_stack.pop()

    def end_trace(
        self,
        result: Any = None,
        error: str = None,
    ) -> Optional[ExecutionTrace]:
        """
        结束追踪

        Args:
            result: 最终结果
            error: 错误信息

        Returns:
            完成的追踪对象
        """
        if self._current_trace:
            self._current_trace.complete(result=result, error=error)

        trace = self._current_trace
        self._current_trace = None
        return trace

    def get_current_trace(self) -> Optional[ExecutionTrace]:
        """获取当前追踪"""
        return self._current_trace

    def add_reasoning(self, reasoning: str) -> None:
        """
        向当前步骤添加思考过程

        Args:
            reasoning: 思考过程描述
        """
        if self._step_stack:
            current_step = self._step_stack[-1]
            current_step.reasoning = reasoning

    def update_confidence(self, confidence: float) -> None:
        """更新当前步骤的置信度"""
        if self._step_stack:
            current_step = self._step_stack[-1]
            current_step.confidence = confidence

    def trace_function(
        self,
        step_type: StepType,
        agent_name: str,
        action: str,
    ) -> Callable:
        """
        装饰器：追踪函数调用

        Example:
            @collector.trace_function(
                step_type=StepType.TOOL_CALL,
                agent_name="AnalysisAgent",
                action="query_latency",
            )
            async def query_latency(region: str) -> dict:
                # 实现
                return {"latency": 50}
        """
        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                with self.trace_step(
                    step_type=step_type,
                    agent_name=agent_name,
                    action=action,
                    input_data={"args": args, "kwargs": kwargs},
                ) as step:
                    result = await func(*args, **kwargs)
                    step.output_data = result
                    return result
            return wrapper
        return decorator


# 全局实例
trace_collector = TraceCollector()
