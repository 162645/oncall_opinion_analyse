"""
LLM 模块
提供统一的 LLM 接入层，支持多后端路由
"""

from .gateway import LLMGateway, LLMConfig, LLMResponse, ChatMessage, get_llm_gateway
from .router import LLMRouter, TaskType

__all__ = [
    "LLMGateway",
    "LLMConfig",
    "LLMResponse",
    "ChatMessage",
    "LLMRouter",
    "TaskType",
    "get_llm_gateway",
]
