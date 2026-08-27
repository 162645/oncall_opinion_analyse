"""
Claude 适配器
"""

import os
from typing import AsyncIterator, Optional, List
import logging

from .base import BaseAdapter
from ..gateway import LLMResponse, ChatMessage

logger = logging.getLogger(__name__)


class ClaudeAdapter(BaseAdapter):
    """Claude API 适配器"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = None

    @property
    def provider(self) -> str:
        return "claude"

    def _get_client(self):
        """获取 Claude 客户端"""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package not installed. "
                    "Install with: pip install anthropic"
                )
        return self._client

    async def generate(
        self,
        prompt: str,
        model: str = "claude-3-sonnet-20240229",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        messages: Optional[List[ChatMessage]] = None,
        **kwargs
    ) -> LLMResponse:
        """生成响应"""
        client = self._get_client()

        # Claude 消息格式
        msg_list = []

        # 添加历史消息
        if messages:
            for msg in messages:
                msg_list.append({"role": msg.role, "content": msg.content})

        # 添加当前提示
        msg_list.append({"role": "user", "content": prompt})

        try:
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "You are a helpful assistant.",
                messages=msg_list,
            )

            # 提取文本内容
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

            return LLMResponse(
                content=content,
                model=response.model,
                provider=self.provider,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
                finish_reason=response.stop_reason or "stop",
            )

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        model: str = "claude-3-sonnet-20240229",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        messages: Optional[List[ChatMessage]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式生成响应"""
        client = self._get_client()

        msg_list = []

        if messages:
            for msg in messages:
                msg_list.append({"role": msg.role, "content": msg.content})

        msg_list.append({"role": "user", "content": prompt})

        try:
            async with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "You are a helpful assistant.",
                messages=msg_list,
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Claude streaming error: {e}")
            raise
