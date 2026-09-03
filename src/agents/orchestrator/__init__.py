"""
增强版 Agent 编排器
支持并行、层级、辩论等多种协作模式
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict


class CollaborationMode(Enum):
    """协作模式"""
    SEQUENTIAL = "sequential"      # 顺序执行
    PARALLEL = "parallel"          # 并行执行
    HIERARCHICAL = "hierarchical"  # 层级执行
    DEBATE = "debate"              # 辩论模式


@dataclass
class AgentContext:
    """Agent 执行上下文"""
    session_id: str
    query: str
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentResult:
    """Agent 执行结果"""
    agent_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    confidence: float = 0.0
    execution_time_ms: int = 0


@dataclass
class OrchestratorResult:
    """编排器执行结果"""
    session_id: str
    mode: CollaborationMode
    agent_results: List[AgentResult]
    final_result: Any
    total_time_ms: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Agent 基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        pass


class ExecutionStrategy(ABC):
    """执行策略基类"""

    @abstractmethod
    async def execute(
        self,
        agents: List[BaseAgent],
        context: AgentContext,
    ) -> List[AgentResult]:
        pass


class SequentialStrategy(ExecutionStrategy):
    """顺序执行策略"""

    async def execute(
        self,
        agents: List[BaseAgent],
        context: AgentContext,
    ) -> List[AgentResult]:
        results = []

        for agent in agents:
            start_time = datetime.now()

            try:
                result = await agent.execute(context)
                result.execution_time_ms = int(
                    (datetime.now() - start_time).total_seconds() * 1000
                )
                results.append(result)

                # 更新上下文
                if result.success and result.data:
                    context.metadata[f"{agent.name}_result"] = result.data

            except Exception as e:
                results.append(AgentResult(
                    agent_name=agent.name,
                    success=False,
                    error=str(e),
                ))

        return results


class ParallelStrategy(ExecutionStrategy):
    """并行执行策略"""

    async def execute(
        self,
        agents: List[BaseAgent],
        context: AgentContext,
    ) -> List[AgentResult]:
        async def run_agent(agent: BaseAgent) -> AgentResult:
            start_time = datetime.now()
            try:
                result = await agent.execute(context)
                result.execution_time_ms = int(
                    (datetime.now() - start_time).total_seconds() * 1000
                )
                return result
            except Exception as e:
                return AgentResult(
                    agent_name=agent.name,
                    success=False,
                    error=str(e),
                )

        # 并行执行所有 Agent
        results = await asyncio.gather(*[
            run_agent(agent) for agent in agents
        ])

        return list(results)


class HierarchicalStrategy(ExecutionStrategy):
    """层级执行策略"""

    def __init__(self, hierarchy: Dict[str, List[str]]):
        """
        Args:
            hierarchy: 层级定义 {"level_1": ["agent_a"], "level_2": ["agent_b", "agent_c"]}
        """
        self.hierarchy = hierarchy

    async def execute(
        self,
        agents: List[BaseAgent],
        context: AgentContext,
    ) -> List[AgentResult]:
        results = []
        agent_map = {agent.name: agent for agent in agents}

        # 按层级顺序执行
        for level in sorted(self.hierarchy.keys()):
            level_agents = [
                agent_map[name]
                for name in self.hierarchy[level]
                if name in agent_map
            ]

            if not level_agents:
                continue

            # 同一层级并行执行
            level_results = await ParallelStrategy().execute(level_agents, context)
            results.extend(level_results)

            # 更新上下文
            for result in level_results:
                if result.success and result.data:
                    context.metadata[f"{result.agent_name}_result"] = result.data

        return results


class DebateStrategy(ExecutionStrategy):
    """
    辩论策略

    多个 Agent 对同一问题提出观点，然后投票选出最佳方案
    """

    def __init__(
        self,
        rounds: int = 2,
        judge_agent: Optional[BaseAgent] = None,
    ):
        self.rounds = rounds
        self.judge_agent = judge_agent

    async def execute(
        self,
        agents: List[BaseAgent],
        context: AgentContext,
    ) -> List[AgentResult]:
        all_proposals = []

        # 多轮辩论
        for round_num in range(self.rounds):
            round_proposals = []

            for agent in agents:
                # 每轮辩论，Agent 可以参考之前的提案
                context.metadata["previous_proposals"] = all_proposals

                start_time = datetime.now()
                result = await agent.execute(context)
                result.execution_time_ms = int(
                    (datetime.now() - start_time).total_seconds() * 1000
                )

                if result.success:
                    round_proposals.append(result)

            all_proposals.extend(round_proposals)

        # 如果有评判 Agent，由它选择最佳方案
        if self.judge_agent:
            context.metadata["all_proposals"] = all_proposals
            judge_result = await self.judge_agent.execute(context)
            all_proposals.append(judge_result)

        return all_proposals


class AgentOrchestrator:
    """
    Agent 编排器

    支持多种协作模式:
    - SEQUENTIAL: 顺序执行，适合有依赖关系
    - PARALLEL: 并行执行，适合独立任务
    - HIERARCHICAL: 层级执行，适合分层处理
    - DEBATE: 辩论模式，适合需要多角度分析
    """

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._strategies: Dict[CollaborationMode, ExecutionStrategy] = {
            CollaborationMode.SEQUENTIAL: SequentialStrategy(),
            CollaborationMode.PARALLEL: ParallelStrategy(),
        }
        self._hierarchy: Optional[Dict[str, List[str]]] = None

    def register_agent(self, agent: BaseAgent):
        """注册 Agent"""
        self._agents[agent.name] = agent

    def set_hierarchy(self, hierarchy: Dict[str, List[str]]):
        """设置层级结构"""
        self._hierarchy = hierarchy
        self._strategies[CollaborationMode.HIERARCHICAL] = HierarchicalStrategy(hierarchy)

    def set_debate_config(self, rounds: int = 2, judge_agent: Optional[BaseAgent] = None):
        """设置辩论配置"""
        self._strategies[CollaborationMode.DEBATE] = DebateStrategy(rounds, judge_agent)

    async def execute(
        self,
        context: AgentContext,
        mode: CollaborationMode = CollaborationMode.SEQUENTIAL,
        agent_names: Optional[List[str]] = None,
    ) -> OrchestratorResult:
        """
        执行编排

        Args:
            context: 执行上下文
            mode: 协作模式
            agent_names: 指定执行的 Agent（可选）

        Returns:
            编排执行结果
        """
        start_time = datetime.now()

        # 获取要执行的 Agent
        if agent_names:
            agents = [
                self._agents[name]
                for name in agent_names
                if name in self._agents
            ]
        else:
            agents = list(self._agents.values())

        if not agents:
            return OrchestratorResult(
                session_id=context.session_id,
                mode=mode,
                agent_results=[],
                final_result=None,
                total_time_ms=0,
                metadata={"error": "No agents available"},
            )

        # 获取执行策略
        strategy = self._strategies.get(mode, SequentialStrategy())

        # 执行
        results = await strategy.execute(agents, context)

        # 汇总结果
        final_result = self._aggregate_results(results, mode)

        total_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return OrchestratorResult(
            session_id=context.session_id,
            mode=mode,
            agent_results=results,
            final_result=final_result,
            total_time_ms=total_time,
            metadata={
                "agent_count": len(agents),
                "successful_count": sum(1 for r in results if r.success),
            },
        )

    def _aggregate_results(
        self,
        results: List[AgentResult],
        mode: CollaborationMode,
    ) -> Dict[str, Any]:
        """汇总结果"""
        if mode == CollaborationMode.PARALLEL:
            # 并行模式：合并各 Agent 结果
            return {
                agent_name: result.data
                for agent_name, result in [(r.agent_name, r) for r in results]
                if result.success
            }

        elif mode == CollaborationMode.DEBATE:
            # 辩论模式：选择最高置信度的结果
            best = max(results, key=lambda r: r.confidence, default=None)
            return best.data if best else None

        else:
            # 顺序模式：返回最后一个成功的结果
            for result in reversed(results):
                if result.success:
                    return result.data

            return None

    def get_agent_status(self) -> Dict[str, Any]:
        """获取 Agent 状态"""
        return {
            "registered_agents": list(self._agents.keys()),
            "available_modes": [m.value for m in CollaborationMode],
        }
