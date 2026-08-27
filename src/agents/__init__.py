"""
Agent 模块
实现增强版多 Agent 协作
"""

from .router import RouterAgent, IntentClassifier, Intent
from .orchestrator import (
    AgentOrchestrator,
    CollaborationMode,
    AgentContext,
    AgentResult,
    BaseAgent,
)
from .llm_agent import (
    LLMAgent,
    DiagnosisLLMAgent,
    AnalysisLLMAgent,
    CodeLLMAgent,
    ChatLLMAgent,
)
from .service import get_agent_service, AgentService, AgentServiceResult

__all__ = [
    "RouterAgent",
    "IntentClassifier",
    "Intent",
    "AgentOrchestrator",
    "CollaborationMode",
    "AgentContext",
    "AgentResult",
    "BaseAgent",
    "LLMAgent",
    "DiagnosisLLMAgent",
    "AnalysisLLMAgent",
    "CodeLLMAgent",
    "ChatLLMAgent",
    "get_agent_service",
    "AgentService",
    "AgentServiceResult",
]
