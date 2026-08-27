"""
LLM 适配器基类
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, List, Dict, Any
from dataclasses import dataclass

from ..gateway import LLMResponse, ChatMessage


class BaseAdapter(ABC):
    """LLM 适配器基类"""

    @property
    @abstractmethod
    def provider(self) -> str:
        """提供商名称"""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        messages: Optional[List[ChatMessage]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        生成响应

        Args:
            prompt: 输入提示
            model: 模型名称
            temperature: 温度
            max_tokens: 最大 token 数
            system_prompt: 系统提示
            messages: 对话历史

        Returns:
            LLMResponse
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        messages: Optional[List[ChatMessage]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式生成响应

        Args:
            prompt: 输入提示
            model: 模型名称
            temperature: 温度
            max_tokens: 最大 token 数
            system_prompt: 系统提示
            messages: 对话历史

        Yields:
            文本片段
        """
        pass

    def _build_messages(
        self,
        prompt: str,
        system_prompt: Optional[str],
        messages: Optional[List[ChatMessage]],
    ) -> List[Dict[str, str]]:
        """构建消息列表"""
        result = []

        # 添加系统提示
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})

        # 添加历史消息
        if messages:
            for msg in messages:
                result.append({"role": msg.role, "content": msg.content})

        # 添加当前提示
        result.append({"role": "user", "content": prompt})

        return result
