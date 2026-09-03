"""
OpenAI 适配器
"""

import os
from typing import AsyncIterator, Optional, List
import logging

from .base import BaseAdapter
from ..gateway import LLMResponse, ChatMessage

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseAdapter):
    """OpenAI API 适配器"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, provider_name: str = "openai"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.provider_name = provider_name
        self._client = None

    @property
    def provider(self) -> str:
        return self.provider_name

    def _get_client(self):
        """获取 OpenAI 客户端"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                kwargs = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = AsyncOpenAI(**kwargs)
            except ImportError:
                raise ImportError(
                    "openai package not installed. "
                    "Install with: pip install openai"
                )
        return self._client

    async def generate(
        self,
        prompt: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        messages: Optional[List[ChatMessage]] = None,
        **kwargs
    ) -> LLMResponse:
        """生成响应"""
        client = self._get_client()

        # 构建消息
        msg_list = self._build_messages(prompt, system_prompt, messages)

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=msg_list,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            choice = response.choices[0]

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                provider=self.provider,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                finish_reason=choice.finish_reason,
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        messages: Optional[List[ChatMessage]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式生成响应"""
        client = self._get_client()

        msg_list = self._build_messages(prompt, system_prompt, messages)

        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=msg_list,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise
