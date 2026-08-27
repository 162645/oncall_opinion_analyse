"""
Agent 核心模块
定义 Agent 基类和协作机制
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class AgentRole(Enum):
    """Agent 角色"""
    DIAGNOSIS = "diagnosis"       # 故障诊断
    KNOWLEDGE = "knowledge"       # 知识检索
    ANALYSIS = "analysis"         # 数据分析
    COORDINATOR = "coordinator"   # 协调器


@dataclass
class AgentContext:
    """Agent 执行上下文"""
    session_id: str
    alert_id: Optional[str] = None
    alert_title: Optional[str] = None
    alert_description: Optional[str] = None
    psm: Optional[str] = None
    region: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    role: AgentRole
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    next_actions: List[str]
    confidence: float
    raw_output: Optional[str] = None
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Agent 基类

    所有专业 Agent 继承此类
    """

    def __init__(
        self,
        role: AgentRole,
        name: str,
        description: str,
        tools: Optional[List[str]] = None,
    ):
        self.role = role
        self.name = name
        self.description = description
        self.tools = tools or []

    @abstractmethod
    def execute(self, context: AgentContext) -> AgentResult:
        """
        执行 Agent 任务

        Args:
            context: 执行上下文

        Returns:
            执行结果
        """
        pass

    def validate_context(self, context: AgentContext) -> bool:
        """验证上下文是否满足执行条件"""
        return True

    def log_action(self, action: str, context: AgentContext):
        """记录 Agent 动作"""
        context.history.append({
            "agent": self.name,
            "role": self.role.value,
            "action": action,
            "timestamp": datetime.now().isoformat(),
        })


class AgentOrchestrator:
    """
    Agent 编排器

    协调多个 Agent 协作完成任务
    """

    def __init__(self):
        self.agents: Dict[AgentRole, BaseAgent] = {}

    def register(self, agent: BaseAgent):
        """注册 Agent"""
        self.agents[agent.role] = agent

    def execute_workflow(
        self,
        context: AgentContext,
        workflow: List[AgentRole],
    ) -> Dict[AgentRole, AgentResult]:
        """
        执行工作流

        Args:
            context: 执行上下文
            workflow: Agent 执行顺序

        Returns:
            各 Agent 执行结果
        """
        results = {}

        for role in workflow:
            if role not in self.agents:
                continue

            agent = self.agents[role]

            if not agent.validate_context(context):
                results[role] = AgentResult(
                    success=False,
                    role=role,
                    findings=[],
                    recommendations=[],
                    next_actions=[],
                    confidence=0.0,
                    error="Context validation failed",
                )
                continue

            result = agent.execute(context)
            results[role] = result

            # 更新上下文
            if result.findings:
                context.metadata[f"{role.value}_findings"] = result.findings

        return results

    def diagnose(self, context: AgentContext) -> Dict[str, Any]:
        """
        诊断故障

        执行顺序: Knowledge -> Analysis -> Diagnosis
        """
        workflow = [
            AgentRole.KNOWLEDGE,
            AgentRole.ANALYSIS,
            AgentRole.DIAGNOSIS,
        ]

        results = self.execute_workflow(context, workflow)

        # 汇总结果
        all_findings = []
        all_recommendations = []
        confidence_scores = []

        for role, result in results.items():
            if result.success:
                all_findings.extend(result.findings)
                all_recommendations.extend(result.recommendations)
                confidence_scores.append(result.confidence)

        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores else 0.0
        )

        return {
            "session_id": context.session_id,
            "findings": all_findings,
            "recommendations": list(set(all_recommendations)),
            "confidence": avg_confidence,
            "agent_results": {
                role.value: {
                    "success": result.success,
                    "findings_count": len(result.findings),
                }
                for role, result in results.items()
            },
        }
