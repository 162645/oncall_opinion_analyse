"""
北邮大模型网关适配器
支持 qwen-latest, qwen-medium, deepseek-medium 等模型
"""

import json
from typing import AsyncIterator, Optional, List, Dict, Any
import httpx

from .base import BaseAdapter
from ..gateway import LLMResponse, ChatMessage


class BUPTGatewayAdapter(BaseAdapter):
    """
    北邮大模型网关适配器

    API 端点: https://llm-gw.bupt.edu.cn/v1
    支持模型:
    - qwen-latest (Qwen 3.5 397B)
    - qwen-medium (Qwen 3.6 35B)
    - deepseek-medium (DeepSeek v4 Flash)
    """

    API_BASE = "https://llm-gw.bupt.edu.cn/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider(self) -> str:
        return "bupt"

    def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def generate(
        self,
        prompt: str,
        model: str = "qwen-medium",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        messages: Optional[List[ChatMessage]] = None,
        **kwargs
    ) -> LLMResponse:
        """生成响应"""
        client = self._get_client()

        # 构建消息
        chat_messages = self._build_messages(prompt, system_prompt, messages)

        # 构建请求
        request_body = {
            "model": model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # 添加额外参数
        if kwargs.get("top_p"):
            request_body["top_p"] = kwargs["top_p"]
        if kwargs.get("frequency_penalty"):
            request_body["frequency_penalty"] = kwargs["frequency_penalty"]
        if kwargs.get("presence_penalty"):
            request_body["presence_penalty"] = kwargs["presence_penalty"]

        try:
            response = await client.post(
                f"{self.API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )

            response.raise_for_status()
            data = response.json()

            # 解析响应
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            usage = data.get("usage", {})

            return LLMResponse(
                content=content,
                model=data.get("model", model),
                provider=self.provider,
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                metadata={
                    "finish_reason": choice.get("finish_reason"),
                    "response_id": data.get("id"),
                },
            )

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error", {}).get("message", str(e.response.text))
            except:
                error_detail = str(e.response.text)

            # 特殊处理无效 token 错误
            if "Invalid token" in error_detail or "invalid token" in error_detail.lower():
                error_detail = "API Key 无效或已过期，请在设置页面配置有效的 API Key"
            elif e.response.status_code == 401:
                error_detail = "认证失败，请检查 API Key 是否正确"

            return LLMResponse(
                content="",
                model=model,
                provider=self.provider,
                error=f"HTTP error: {e.response.status_code} - {error_detail}",
            )
        except Exception as e:
            return LLMResponse(
                content="",
                model=model,
                provider=self.provider,
                error=str(e),
            )

    async def generate_stream(
        self,
        prompt: str,
        model: str = "qwen-medium",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        messages: Optional[List[ChatMessage]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式生成响应"""
        client = self._get_client()

        # 构建消息
        chat_messages = self._build_messages(prompt, system_prompt, messages)

        # 构建请求
        request_body = {
            "model": model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with client.stream(
                "POST",
                f"{self.API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # 去掉 "data: " 前缀

                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")

                            if content:
                                yield content

                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            yield f"[Error] HTTP error: {e.response.status_code}"
        except Exception as e:
            yield f"[Error] {str(e)}"

    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        return [
            {
                "id": "qwen-latest",
                "name": "Qwen 3.5 (397B-A17B)",
                "description": "推理能力强、逻辑缜密，擅长处理高难度复杂任务",
                "latency": "medium",
                "context_length": 32768,
            },
            {
                "id": "qwen-medium",
                "name": "Qwen 3.6 (35B-A3B)",
                "description": "均衡实用，兼顾实用性与效率",
                "latency": "fast",
                "context_length": 32768,
            },
            {
                "id": "deepseek-medium",
                "name": "DeepSeek v4 Flash",
                "description": "响应速度极快，适合快速处理常规任务",
                "latency": "fast",
                "context_length": 64000,
            },
        ]
