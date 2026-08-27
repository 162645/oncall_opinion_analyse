"""
LLM 路由
提供 LLM 统一接口 API
"""

import logging
import os
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.llm import LLMConfig, LLMResponse, TaskType

router = APIRouter()
logger = logging.getLogger(__name__)


# ===== 请求/响应模型 =====

class GenerateRequest(BaseModel):
    """生成请求"""
    prompt: str
    provider: Optional[str] = "deepseek"  # 默认使用 DeepSeek
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    system_prompt: Optional[str] = None
    stream: Optional[bool] = False
    task_type: Optional[str] = None  # simple, complex, code, diagnosis, etc.


class MessageItem(BaseModel):
    """消息项"""
    role: str
    content: str


class ChatRequest(BaseModel):
    """对话请求"""
    messages: List[MessageItem]
    provider: Optional[str] = "deepseek"  # 默认使用 DeepSeek
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    system_prompt: Optional[str] = None


class SmartGenerateRequest(BaseModel):
    """智能生成请求"""
    prompt: str
    task_type: Optional[str] = None


class GenerateResponse(BaseModel):
    """生成响应"""
    success: bool
    content: str
    model: str
    provider: str
    usage: dict
    latency_ms: int
    cost_estimate: Optional[float] = None


class ProviderInfo(BaseModel):
    """提供商信息"""
    name: str
    display_name: str
    models: List[dict]


# ===== API 端点 =====

@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    生成响应

    支持多后端:
    - bupt: Qwen 3.5, Qwen 3.6, DeepSeek v4 (默认，免费)
    - openai: GPT-4, GPT-4o, GPT-3.5
    - claude: Claude-3 Opus, Sonnet, Haiku
    """
    from src.llm import get_llm_gateway

    gateway = get_llm_gateway()

    # 确定默认模型
    default_models = {
        "deepseek": "deepseek-chat",
        "bupt": "qwen-medium",
        "openai": "gpt-4o",
        "claude": "claude-3-sonnet-20240229",
    }

    # 构建配置
    config = LLMConfig(
        provider=request.provider,
        model=request.model or default_models.get(request.provider, "deepseek-chat"),
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        system_prompt=request.system_prompt,
        stream=request.stream,
    )

    # 解析任务类型
    task_type = None
    if request.task_type:
        try:
            task_type = TaskType(request.task_type)
        except ValueError:
            pass

    try:
        response = await gateway.generate(
            prompt=request.prompt,
            config=config,
        )

        return GenerateResponse(
            success=True,
            content=response.content,
            model=response.model,
            provider=response.provider,
            usage=response.usage,
            latency_ms=response.latency_ms,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-generate", response_model=GenerateResponse)
async def smart_generate(request: SmartGenerateRequest):
    """
    智能生成 - 自动选择最优模型

    根据任务类型和内容自动选择最适合的模型
    """
    from src.llm import get_llm_gateway

    gateway = get_llm_gateway()

    # 解析任务类型
    task_type = None
    if request.task_type:
        try:
            task_type = TaskType(request.task_type)
        except ValueError:
            pass

    try:
        response = await gateway.smart_generate(
            prompt=request.prompt,
            task_type=task_type,
        )

        return GenerateResponse(
            success=True,
            content=response.content,
            model=response.model,
            provider=response.provider,
            usage=response.usage,
            latency_ms=response.latency_ms,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-with-fallback", response_model=GenerateResponse)
async def generate_with_fallback(request: GenerateRequest):
    """
    带故障转移的生成

    主提供商失败时自动切换到备用提供商
    """
    from src.llm import get_llm_gateway

    gateway = get_llm_gateway()

    primary = request.provider
    # 仅在明确配置时回退到其他提供商，默认链路保持 DeepSeek，避免无配置网关导致长时间等待。
    fallback = "deepseek" if primary != "deepseek" else "openai"

    try:
        response = await gateway.generate_with_fallback(
            prompt=request.prompt,
            primary=primary,
            fallback=fallback,
        )

        return GenerateResponse(
            success=True,
            content=response.content,
            model=response.model,
            provider=response.provider,
            usage=response.usage,
            latency_ms=response.latency_ms,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=GenerateResponse)
async def chat(request: ChatRequest):
    """
    对话接口

    支持多轮对话历史
    """
    from src.llm import get_llm_gateway, ChatMessage

    gateway = get_llm_gateway()

    # 确定默认模型
    default_models = {
        "deepseek": "deepseek-chat",
        "openai": "gpt-4o",
        "claude": "claude-3-sonnet-20240229",
    }

    # 转换消息格式
    messages = [ChatMessage(role=m.role, content=m.content) for m in request.messages]

    config = LLMConfig(
        provider=request.provider,
        model=request.model or default_models.get(request.provider, "deepseek-chat"),
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        system_prompt=request.system_prompt,
    )

    try:
        response = await gateway.generate(
            prompt="",  # 消息已包含在 messages 中
            config=config,
            messages=messages,
        )

        return GenerateResponse(
            success=True,
            content=response.content,
            model=response.model,
            provider=response.provider,
            usage=response.usage,
            latency_ms=response.latency_ms,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def list_providers():
    """获取可用的 LLM 提供商"""
    from src.llm import get_llm_gateway

    gateway = get_llm_gateway()

    # 确保初始化完成
    try:
        await gateway.initialize()
    except Exception as e:
        # 初始化失败时仍返回默认 provider
        logger.warning(f"Failed to initialize LLM gateway: {e}")

    # 获取已初始化的 providers
    try:
        available_providers = gateway.get_available_providers()
    except:
        available_providers = ["bupt"]

    providers = []

    # DeepSeek 为生产默认提供商
    if "deepseek" in available_providers or os.getenv("DEEPSEEK_API_KEY"):
        providers.append({
            "name": "deepseek",
            "display_name": "DeepSeek",
            "models": [
                {"id": "deepseek-chat", "name": "DeepSeek Chat", "max_tokens": 8192, "tier": "fast"},
                {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner", "max_tokens": 65536, "tier": "medium"},
            ],
        })

    # BUPT 网关（仅在实际配置时显示）
    if "bupt" in available_providers:
        providers.append({
            "name": "bupt",
            "display_name": "BUPT 网关 (免费)",
            "models": [
                {
                    "id": "qwen-latest",
                    "name": "Qwen 3.5 (397B)",
                    "max_tokens": 32768,
                    "tier": "medium",
                    "description": "推理能力强、逻辑缜密，擅长处理高难度复杂任务"
                },
                {
                    "id": "qwen-medium",
                    "name": "Qwen 3.6 (35B)",
                    "max_tokens": 32768,
                    "tier": "fast",
                    "description": "均衡实用，兼顾实用性与效率"
                },
                {
                    "id": "deepseek-medium",
                    "name": "DeepSeek v4 Flash",
                    "max_tokens": 64000,
                    "tier": "fast",
                    "description": "响应速度极快，适合快速处理常规任务"
                },
            ],
        })

    # OpenAI
    if "openai" in available_providers:
        providers.append({
            "name": "openai",
            "display_name": "OpenAI",
            "models": [
                {"id": "gpt-4o", "name": "GPT-4o", "max_tokens": 128000, "tier": "fast"},
                {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "max_tokens": 128000, "tier": "medium"},
                {"id": "gpt-4", "name": "GPT-4", "max_tokens": 8192, "tier": "slow"},
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "max_tokens": 16384, "tier": "fast"},
            ],
        })

    # Claude
    if "claude" in available_providers:
        providers.append({
            "name": "claude",
            "display_name": "Claude (Anthropic)",
            "models": [
                {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "max_tokens": 200000, "tier": "slow"},
                {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "max_tokens": 200000, "tier": "medium"},
                {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "max_tokens": 200000, "tier": "fast"},
            ],
        })

    return {
        "success": True,
        "providers": providers,
        "connection_note": "当前默认使用 DeepSeek 官方 API；如连接失败，请检查服务器出口网络和 API Key。"
    }


@router.post("/config")
async def configure_llm(request: dict):
    """
    配置 LLM API Keys

    接收并保存 API Keys 到环境变量或配置文件
    """
    import os

    bupt_api_key = request.get("bupt_api_key")
    deepseek_api_key = request.get("deepseek_api_key")
    openai_api_key = request.get("openai_api_key")
    anthropic_api_key = request.get("anthropic_api_key")

    # 设置环境变量（仅当前会话有效）
    if bupt_api_key:
        os.environ["BUPT_API_KEY"] = bupt_api_key
    if deepseek_api_key:
        os.environ["DEEPSEEK_API_KEY"] = deepseek_api_key
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key
    if anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key

    # 重新初始化 gateway 以使用新的 API Keys
    from src.llm import get_llm_gateway
    gateway = get_llm_gateway()
    gateway._initialized = False
    gateway._adapters = {}

    return {
        "success": True,
        "message": "API Keys 配置已更新，将在下次请求时生效"
    }


@router.get("/test-connection")
async def test_llm_connection():
    """测试 LLM 连接状态"""
    from src.llm import get_llm_gateway
    import httpx
    import os

    gateway = get_llm_gateway()

    # 获取默认 API Key
    default_bupt_key = os.getenv("BUPT_API_KEY")

    results = {
        "bupt": {"status": "unknown", "message": ""},
        "deepseek": {"status": "not_configured", "message": "未配置 API Key"},
        "openai": {"status": "not_configured", "message": "未配置 API Key"},
        "claude": {"status": "not_configured", "message": "未配置 API Key"},
    } 

    # 生产环境默认使用 DeepSeek；优先测试实际配置的模型服务
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(
                    f"{os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {deepseek_key}", "Content-Type": "application/json"},
                    json={"model": os.getenv("LLM_MODEL", "deepseek-chat"), "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                )
            results["deepseek"] = {"status": "connected" if response.status_code == 200 else "error", "message": "连接成功" if response.status_code == 200 else f"HTTP {response.status_code}"}
        except httpx.TimeoutException:
            results["deepseek"] = {"status": "timeout", "message": "连接超时"}
        except Exception as e:
            results["deepseek"] = {"status": "error", "message": str(e)}

    # 只有显式配置 BUPT Key 时才测试旧网关，避免每次刷新设置页都等待外部网络超时。
    if default_bupt_key:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(
                    "https://llm-gw.bupt.edu.cn/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {default_bupt_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "qwen-medium",
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 5,
                    },
                )
            if response.status_code == 200:
                results["bupt"] = {"status": "connected", "message": "连接成功 (使用默认 Key)"}
            else:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                results["bupt"] = {"status": "error", "message": error_msg}
        except httpx.ConnectError:
            results["bupt"] = {"status": "network_error", "message": "网络连接失败，请检查网络"}
        except httpx.TimeoutException:
            results["bupt"] = {"status": "timeout", "message": "连接超时"}
        except Exception as e:
            results["bupt"] = {"status": "error", "message": str(e)}
    else:
      results["bupt"] = {"status": "not_configured", "message": "未配置（已停用旧网关检测）"}

    # 检查其他 provider 配置
    if os.getenv("OPENAI_API_KEY"):
        results["openai"] = {"status": "configured", "message": "已配置 API Key"}
    if os.getenv("ANTHROPIC_API_KEY"):
        results["claude"] = {"status": "configured", "message": "已配置 API Key"}

    return {
        "success": True,
        "results": results,
        "recommendation": "BUPT 网关已预配置默认 API Key，可直接使用。如遇问题请检查网络连接。"
    }


@router.get("/costs")
async def get_costs():
    """获取成本统计"""
    from src.llm import get_llm_gateway

    gateway = get_llm_gateway()

    return {
        "success": True,
        "costs": gateway.get_cost_summary(),
    }


@router.post("/classify-task")
async def classify_task(request: SmartGenerateRequest):
    """分类任务类型"""
    from src.llm.router import LLMRouter

    router = LLMRouter()

    task_type = router.classify_task(request.prompt)
    complexity = router.estimate_complexity(request.prompt)

    provider, model = router.select(request.prompt)

    return {
        "success": True,
        "task_type": task_type.value,
        "complexity": complexity,
        "recommended": {
            "provider": provider,
            "model": model,
        },
    }
