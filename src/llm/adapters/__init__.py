"""
LLM 适配器模块
"""

from .base import BaseAdapter
from .openai_adapter import OpenAIAdapter
from .claude_adapter import ClaudeAdapter
from .bupt_adapter import BUPTGatewayAdapter

__all__ = [
    "BaseAdapter",
    "OpenAIAdapter",
    "ClaudeAdapter",
    "BUPTGatewayAdapter",
]
