"""
ReAct Agent 实现
推理-行动循环 (Reasoning + Acting)
"""

import time
import re
import json
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from .types import ReActStep, ReActState, ReActTrace

if TYPE_CHECKING:
    from src.agents import AgentContext, AgentResult


class ReActAgent:
    """
    ReAct Agent: 推理-行动循环

    核心思想:
    1. Thought: 分析当前状态，思考下一步
    2. Action: 选择并执行工具
    3. Observation: 观察执行结果
    4. 重复直到得出最终答案

    使用示例:
    ```python
    agent = ReActAgent(tools={
        "search": search_tool,
        "query": query_tool,
    })

    result = await agent.execute(
        query="分析新加坡区域网络延迟突增的原因",
        context=context
    )
    ```
    """

    # 思考提示模板
    THINK_PROMPT = """你是一个智能运维诊断助手。请分析当前任务并思考下一步行动。

任务: {query}

可用工具:
{tools_desc}

历史步骤:
{history}

请按以下格式输出:
Thought: 你的思考过程
Action: 工具名称
Action Input: {{"param1": "value1", ...}}

或者如果已经有最终答案:
Thought: 我已经找到答案
Final Answer: 最终结论
"""

    def __init__(
        self,
        tools: Optional[Dict[str, Callable]] = None,
        llm: Optional[Any] = None,
        max_steps: int = 10,
        verbose: bool = False,
    ):
        """
        初始化 ReAct Agent

        Args:
            tools: 可用工具字典 {name: callable}
            llm: 大语言模型实例 (需要有 generate 方法)
            max_steps: 最大步数
            verbose: 是否打印详细日志
        """
        self.tools = tools or {}
        self.llm = llm
        self.max_steps = max_steps
        self.verbose = verbose

    def register_tool(self, name: str, func: Callable) -> None:
        """注册工具"""
        self.tools[name] = func

    def _get_tools_description(self) -> str:
        """获取工具描述"""
        descriptions = []
        for name, func in self.tools.items():
            desc = getattr(func, "__doc__", "无描述")
            descriptions.append(f"- {name}: {desc.strip() if desc else '无描述'}")
        return "\n".join(descriptions)

    def _format_history(self, steps: List[ReActStep]) -> str:
        """格式化历史步骤"""
        if not steps:
            return "无"

        lines = []
        for step in steps:
            lines.append(f"Step {step.step_id}:")
            if step.thought:
                lines.append(f"  Thought: {step.thought}")
            if step.action:
                lines.append(f"  Action: {step.action}")
                lines.append(f"  Action Input: {step.action_input}")
            if step.observation:
                lines.append(f"  Observation: {step.observation[:200]}...")

        return "\n".join(lines)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应"""
        result = {
            "thought": None,
            "action": None,
            "action_input": None,
            "final_answer": None,
        }

        # 提取 Thought
        thought_match = re.search(r"Thought:\s*(.+?)(?=\nAction:|\nFinal Answer:|$)", response, re.DOTALL)
        if thought_match:
            result["thought"] = thought_match.group(1).strip()

        # 提取 Final Answer
        final_match = re.search(r"Final Answer:\s*(.+?)$", response, re.DOTALL)
        if final_match:
            result["final_answer"] = final_match.group(1).strip()
            return result

        # 提取 Action
        action_match = re.search(r"Action:\s*(\w+)", response)
        if action_match:
            result["action"] = action_match.group(1).strip()

        # 提取 Action Input
        input_match = re.search(r"Action Input:\s*(\{.+?\})", response, re.DOTALL)
        if input_match:
            try:
                result["action_input"] = json.loads(input_match.group(1))
            except json.JSONDecodeError:
                result["action_input"] = {"raw": input_match.group(1)}

        return result

    async def _think(self, query: str, steps: List[ReActStep]) -> Dict[str, Any]:
        """思考阶段"""
        if self.llm is None:
            # 无 LLM 时使用简单规则
            return self._rule_based_think(query, steps)

        prompt = self.THINK_PROMPT.format(
            query=query,
            tools_desc=self._get_tools_description(),
            history=self._format_history(steps),
        )

        response = await self.llm.generate(prompt)
        return self._parse_response(response)

    def _rule_based_think(self, query: str, steps: List[ReActStep]) -> Dict[str, Any]:
        """基于规则的思考 (无 LLM 时)"""
        query_lower = query.lower()

        # 根据查询内容选择工具
        if "延迟" in query_lower or "latency" in query_lower:
            if "search" in self.tools:
                return {
                    "thought": "查询涉及网络延迟，先搜索相关知识库",
                    "action": "search",
                    "action_input": {"query": query},
                }
            elif "query" in self.tools:
                return {
                    "thought": "查询涉及网络延迟，直接查询监控数据",
                    "action": "query",
                    "action_input": {"metric": "latency"},
                }

        if "错误" in query_lower or "error" in query_lower:
            if "search" in self.tools:
                return {
                    "thought": "查询涉及错误，搜索相关案例",
                    "action": "search",
                    "action_input": {"query": query},
                }

        # 默认搜索
        if "search" in self.tools:
            return {
                "thought": "先搜索知识库获取相关信息",
                "action": "search",
                "action_input": {"query": query},
            }

        return {
            "thought": "无可用工具，直接给出答案",
            "final_answer": f"关于 '{query}' 的问题，需要更多信息才能给出准确答案。",
        }

    async def _act(self, action: str, action_input: Dict[str, Any]) -> Any:
        """行动阶段"""
        if action not in self.tools:
            raise ValueError(f"Unknown action: {action}")

        tool = self.tools[action]

        # 执行工具
        if callable(tool):
            import asyncio
            if asyncio.iscoroutinefunction(tool):
                result = await tool(**action_input)
            else:
                result = tool(**action_input)
        else:
            result = tool

        return result

    async def execute(
        self,
        query: str,
        context: Optional["AgentContext"] = None,
    ) -> "AgentResult":
        """
        执行 ReAct 循环

        Args:
            query: 用户查询
            context: Agent 上下文

        Returns:
            AgentResult: 执行结果
        """
        from src.agents import AgentResult

        trace = ReActTrace(query=query)
        steps: List[ReActStep] = []

        for step_id in range(1, self.max_steps + 1):
            start_time = time.time()

            # 思考
            think_result = await self._think(query, steps)

            step = ReActStep(
                step_id=step_id,
                state=ReActState.THINKING,
                thought=think_result.get("thought"),
            )

            # 检查是否有最终答案
            if think_result.get("final_answer"):
                step.state = ReActState.FINISHED
                step.duration_ms = int((time.time() - start_time) * 1000)
                trace.add_step(step)
                trace.final_answer = think_result["final_answer"]
                trace.success = True

                if self.verbose:
                    print(f"[ReAct] Final Answer: {think_result['final_answer']}")

                return AgentResult(
                    success=True,
                    data={
                        "answer": think_result["final_answer"],
                        "trace": trace.to_dict(),
                    },
                )

            # 执行行动
            action = think_result.get("action")
            action_input = think_result.get("action_input", {})

            if not action:
                step.state = ReActState.FAILED
                step.error = "No action specified"
                step.duration_ms = int((time.time() - start_time) * 1000)
                trace.add_step(step)
                continue

            step.action = action
            step.action_input = action_input
            step.state = ReActState.ACTING

            try:
                if self.verbose:
                    print(f"[ReAct] Action: {action}, Input: {action_input}")

                result = await self._act(action, action_input)
                step.result = result
                step.observation = str(result)[:500]  # 限制观察长度
                step.state = ReActState.OBSERVING

                if self.verbose:
                    print(f"[ReAct] Observation: {step.observation[:100]}...")

            except Exception as e:
                step.error = str(e)
                step.state = ReActState.FAILED

            step.duration_ms = int((time.time() - start_time) * 1000)
            trace.add_step(step)
            steps.append(step)

        # 达到最大步数
        trace.final_answer = "达到最大步数限制，未能得出最终答案"
        trace.success = False

        return AgentResult(
            success=False,
            error="Max steps reached",
            data={"trace": trace.to_dict()},
        )
