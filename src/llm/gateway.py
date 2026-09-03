"""
LLM Gateway
统一的 LLM 接入层，支持多后端路由
"""

import os
from typing import AsyncIterator, Optional, Dict, Any, List
from dataclasses import dataclass, field
import asyncio
import time
import logging
from src.observability import get_telemetry

from .router import LLMRouter, TaskType

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "deepseek"))
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "deepseek-chat"))
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False
    top_p: float = 1.0
    system_prompt: Optional[str] = None


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: int = 0
    finish_reason: str = "stop"
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatMessage:
    """对话消息"""
    role: str  # system, user, assistant
    content: str


class LLMGateway:
    """
    LLM 统一网关

    功能:
    1. 多后端支持 (OpenAI, Claude)
    2. 智能路由 (根据任务选择最优模型)
    3. 自动故障转移
    4. 流式响应
    5. 成本追踪
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._adapters: Dict[str, "BaseAdapter"] = {}
        self._router = LLMRouter()
        self._cost_tracker: Dict[str, float] = {}
        self._initialized = False

    async def initialize(self):
        """初始化适配器"""
        if self._initialized:
            return

        from .adapters import OpenAIAdapter, ClaudeAdapter, BUPTGatewayAdapter

        self._adapters = {}

        # 初始化 BUPT 网关（默认，优先初始化）
        bupt_api_key = os.getenv("BUPT_API_KEY")
        if bupt_api_key:
            try:
                self._adapters["bupt"] = BUPTGatewayAdapter(bupt_api_key)
                logger.info("BUPT Gateway adapter initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize BUPT adapter: {e}")

        # 初始化 OpenAI（如果配置了 API Key）
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            try:
                self._adapters["openai"] = OpenAIAdapter(openai_api_key)
                logger.info("OpenAI adapter initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI adapter: {e}")

        # DeepSeek 使用 OpenAI-compatible API
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if deepseek_api_key:
            try:
                self._adapters["deepseek"] = OpenAIAdapter(
                    deepseek_api_key,
                    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                    provider_name="deepseek",
                )
                logger.info("DeepSeek adapter initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize DeepSeek adapter: {e}")

        # 初始化 Claude（如果配置了 API Key）
        claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        if claude_api_key:
            try:
                self._adapters["claude"] = ClaudeAdapter(claude_api_key)
                logger.info("Claude adapter initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Claude adapter: {e}")

        # 确保至少有一个适配器可用
        if not self._adapters:
            raise RuntimeError("No LLM adapters available. Please configure at least one provider.")

        self._initialized = True
        logger.info(f"LLM Gateway initialized with providers: {list(self._adapters.keys())}")

    def _ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            asyncio.create_task(self.initialize())

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        messages: Optional[List[ChatMessage]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        同步生成响应

        Args:
            prompt: 输入提示
            config: LLM 配置
            messages: 对话历史（可选）
            **kwargs: 其他参数

        Returns:
            LLMResponse
        """
        await self.initialize()

        cfg = config or self.config

        # 检查适配器是否存在
        if cfg.provider not in self._adapters:
            # 尝试回退到可用的适配器
            available_providers = list(self._adapters.keys())
            if available_providers:
                fallback_provider = available_providers[0]
                logger.warning(
                    f"Provider '{cfg.provider}' not available, "
                    f"falling back to '{fallback_provider}'"
                )
                cfg = LLMConfig(
                    provider=fallback_provider,
                    model="qwen-medium" if fallback_provider == "bupt" else cfg.model,
                    temperature=cfg.temperature,
                    max_tokens=cfg.max_tokens,
                    system_prompt=cfg.system_prompt,
                )
            else:
                raise RuntimeError(f"Provider '{cfg.provider}' not available and no fallback found")

        adapter = self._adapters[cfg.provider]

        start_time = time.time()

        try:
            with get_telemetry().tracer.start_as_current_span("llm.generate", attributes={
                "gen_ai.provider.name": cfg.provider,
                "gen_ai.request.model": cfg.model,
                "gen_ai.request.max_tokens": cfg.max_tokens,
            }) as span:
                response = await adapter.generate(
                    prompt=prompt,
                    model=cfg.model,
                    temperature=cfg.temperature,
                    max_tokens=cfg.max_tokens,
                    system_prompt=cfg.system_prompt,
                    messages=messages,
                    top_p=cfg.top_p,
                    **kwargs
                )
                span.set_attribute("gen_ai.usage.input_tokens", response.usage.get("prompt_tokens", 0))
                span.set_attribute("gen_ai.usage.output_tokens", response.usage.get("completion_tokens", 0))

            # 记录延迟
            response.latency_ms = int((time.time() - start_time) * 1000)

            # 追踪成本
            self._track_cost(response)

            return response

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        messages: Optional[List[ChatMessage]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式生成响应

        Args:
            prompt: 输入提示
            config: LLM 配置
            messages: 对话历史

        Yields:
            文本片段
        """
        await self.initialize()

        cfg = config or self.config

        # 检查适配器是否存在
        if cfg.provider not in self._adapters:
            available_providers = list(self._adapters.keys())
            if available_providers:
                fallback_provider = available_providers[0]
                logger.warning(
                    f"Provider '{cfg.provider}' not available, "
                    f"falling back to '{fallback_provider}'"
                )
                cfg = LLMConfig(
                    provider=fallback_provider,
                    model="qwen-medium" if fallback_provider == "bupt" else cfg.model,
                    temperature=cfg.temperature,
                    max_tokens=cfg.max_tokens,
                    system_prompt=cfg.system_prompt,
                )
            else:
                raise RuntimeError(f"Provider '{cfg.provider}' not available and no fallback found")

        adapter = self._adapters[cfg.provider]

        async for chunk in adapter.generate_stream(
            prompt=prompt,
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            system_prompt=cfg.system_prompt,
            messages=messages,
            **kwargs
        ):
            yield chunk

    async def generate_with_fallback(
        self,
        prompt: str,
        primary: str = "openai",
        fallback: str = "claude",
        task_type: Optional[TaskType] = None,
        **kwargs
    ) -> LLMResponse:
        """
        带故障转移的生成

        Args:
            prompt: 输入提示
            primary: 首选提供商
            fallback: 备用提供商
            task_type: 任务类型

        Returns:
            LLMResponse
        """
        # 使用智能路由选择模型
        provider, model = self._router.select(prompt, task_type, prefer_provider=primary)

        try:
            config = LLMConfig(provider=provider, model=model)
            return await self.generate(prompt, config=config, **kwargs)

        except Exception as e:
            logger.warning(f"Primary provider {provider} failed: {e}, trying fallback")

            # 尝试备用
            provider, model = self._router.select(prompt, task_type, prefer_provider=fallback)
            config = LLMConfig(provider=provider, model=model)

            return await self.generate(prompt, config=config, **kwargs)

    async def smart_generate(
        self,
        prompt: str,
        task_type: Optional[TaskType] = None,
        **kwargs
    ) -> LLMResponse:
        """
        智能生成 - 自动选择最优模型

        根据任务类型和内容自动选择最适合的模型
        """
        # 自动路由选择
        provider, model = self._router.select(prompt, task_type)

        config = LLMConfig(provider=provider, model=model)

        return await self.generate(prompt, config=config, **kwargs)

    def _track_cost(self, response: LLMResponse):
        """追踪成本"""
        # 简单的成本估算
        provider = response.provider
        usage = response.usage

        # 输入和输出 token 数
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # 成本估算 (每 1K tokens)
        cost_rates = {
            "openai": {
                "gpt-4": {"input": 0.03, "output": 0.06},
                "gpt-4-turbo": {"input": 0.01, "output": 0.03},
                "gpt-4o": {"input": 0.005, "output": 0.015},
                "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            },
            "claude": {
                "claude-3-opus": {"input": 0.015, "output": 0.075},
                "claude-3-sonnet": {"input": 0.003, "output": 0.015},
                "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            },
            "bupt": {
                "qwen-latest": {"input": 0.0, "output": 0.0},  # 免费使用
                "qwen-medium": {"input": 0.0, "output": 0.0},
                "deepseek-medium": {"input": 0.0, "output": 0.0},
            },
        }

        model_rates = cost_rates.get(provider, {}).get(response.model, {})
        input_rate = model_rates.get("input", 0.01)
        output_rate = model_rates.get("output", 0.03)

        cost = (input_tokens / 1000 * input_rate) + (output_tokens / 1000 * output_rate)

        self._cost_tracker[provider] = self._cost_tracker.get(provider, 0) + cost

    def get_cost_summary(self) -> Dict[str, float]:
        """获取成本统计"""
        return dict(self._cost_tracker)

    def estimate_tokens(self, text: str) -> int:
        """估算 Token 数量"""
        # 中文约 1.5 字/token, 英文约 4 字符/token
        chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)

    def get_available_providers(self) -> List[str]:
        """获取可用的提供商列表"""
        return list(self._adapters.keys())


# 全局实例
_gateway: Optional[LLMGateway] = None


def get_llm_gateway() -> LLMGateway:
    """获取 LLM 网关实例"""
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway
