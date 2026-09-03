"""
Agent 协作模块
实现多 Agent 协作进行故障诊断
"""

from .core import BaseAgent, AgentRole, AgentContext
from .specialists import DiagnosisAgent, KnowledgeAgent, AnalysisAgent

__all__ = [
    "BaseAgent",
    "AgentRole",
    "AgentContext",
    "DiagnosisAgent",
    "KnowledgeAgent",
    "AnalysisAgent",
]
