"""
对话路由
提供 Agent 对话 API，支持会话持久化
"""

from datetime import datetime
from typing import List, Optional, Literal
import uuid
import json
import time

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.harness import get_harness
from src.visualization import AdvancedVisualizationService
from src.session import get_session_service

router = APIRouter()


# ===== 请求/响应模型 =====

class ChatMessage(BaseModel):
    """对话消息"""
    role: str  # user, assistant, system
    content: str
    timestamp: Optional[str] = None
    metadata: Optional[dict] = None


class ChatRequest(BaseModel):
    """对话请求"""
    session_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=8000)
    mode: Literal["sequential", "parallel", "hierarchical", "debate"] = "sequential"
    context: Optional[dict] = None
    # 模型选择
    provider: Optional[str] = None  # openai, claude
    model: Optional[str] = None  # gpt-4o, claude-3-sonnet, etc.


class TraceStep(BaseModel):
    """追踪步骤"""
    step_id: int
    step_type: str
    agent_name: str
    action: str
    reasoning: Optional[str] = None
    duration_ms: int
    status: str
    tokens: Optional[dict] = None  # Token 使用信息


class TokenUsage(BaseModel):
    """Token 使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    """对话响应"""
    success: bool
    session_id: str
    message: str
    trace: Optional[List[TraceStep]] = None
    chart_data: Optional[dict] = None
    confidence: Optional[float] = None
    mode: str
    skill_recommendation: Optional[dict] = None
    # 模型信息
    provider: Optional[str] = None
    model: Optional[str] = None
    # Token 使用统计
    token_usage: Optional[TokenUsage] = None
    total_duration_ms: int = 0
    # Evidence-driven Harness contract
    verdict: Optional[str] = None
    evidence: Optional[List[dict]] = None
    run_id: Optional[str] = None


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    mode: str


class SessionListResponse(BaseModel):
    """会话列表响应"""
    success: bool
    sessions: List[SessionInfo]


class SessionDetailResponse(BaseModel):
    """会话详情响应"""
    success: bool
    session: dict


# ===== API 端点 =====

@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    发送对话消息

    支持多种 Agent 模式:
    - sequential: 顺序执行
    - parallel: 并行执行
    - hierarchical: 层级执行
    - debate: 辩论模式
    """
    session_service = get_session_service()

    # 创建或获取会话
    session_id = request.session_id or str(uuid.uuid4())
    session = await session_service.get_session(session_id)

    if not session:
        session = await session_service.create_session(
            session_id=session_id,
            mode=request.mode or "sequential"
        )

    # 添加用户消息
    await session_service.add_message(
        session_id=session_id,
        role="user",
        content=request.message
    )

    # 统一进入证据驱动 Harness；mode 仅保留为兼容字段，不再切换多套编排器。
    started = time.perf_counter()
    result = await get_harness().execute(
        query=request.message,
        session_id=session_id,
        metadata={"mode": request.mode, "provider": request.provider, "model": request.model, **(request.context or {})},
    )
    total_duration_ms = int((time.perf_counter() - started) * 1000)

    # 构建追踪步骤
    trace = [
        TraceStep(
            step_id=step.get("step_id", i + 1),
            step_type=step.get("step_type", "harness_node"),
            agent_name=step.get("agent_name", "harness"),
            action=step.get("action", "execute"),
            reasoning=step.get("reasoning"),
            duration_ms=step.get("duration_ms", 0),
            status=step.get("status", "success"),
            tokens=step.get("tokens"),
        )
        for i, step in enumerate(result.trace)
    ]

    # 计算 token 使用总量
    total_tokens = TokenUsage()
    # 当前 Harness 的模型调用可选，未发生 LLM 调用时明确返回 0，而不是伪造 token 指标。

    # 添加助手消息
    await session_service.add_message(
        session_id=session_id,
        role="assistant",
        content=result.message,
        metadata={
            "trace": [t.model_dump() for t in trace],
            "confidence": result.confidence,
            "chart_data": result.chart_data,
            "token_usage": total_tokens.model_dump(),
            "verdict": result.chart_data.get("verdict") if result.chart_data else None,
            "evidence": result.chart_data.get("evidence", []) if result.chart_data else [],
            "run_id": result.state.get("run_id"),
        }
    )

    return ChatResponse(
        success=result.success,
        session_id=session_id,
        message=result.message,
        trace=trace,
        chart_data=result.chart_data,
        confidence=result.confidence,
        mode=request.mode,
        skill_recommendation=None,
        provider=request.provider,
        model=request.model,
        token_usage=total_tokens,
        total_duration_ms=total_duration_ms,
        verdict=result.chart_data.get("verdict") if result.chart_data else None,
        evidence=result.chart_data.get("evidence", []) if result.chart_data else [],
        run_id=result.state.get("run_id"),
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    """获取会话列表"""
    session_service = get_session_service()
    sessions = await session_service.list_sessions(limit=limit, offset=offset)

    return SessionListResponse(
        success=True,
        sessions=[
            SessionInfo(
                session_id=s["session_id"],
                title=s.get("title", "新对话"),
                created_at=s["created_at"],
                updated_at=s.get("updated_at", s["created_at"]),
                message_count=s["message_count"],
                mode=s["mode"],
            )
            for s in sessions
        ],
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str):
    """获取会话详情（包含历史消息）"""
    session_service = get_session_service()
    session = await session_service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetailResponse(
        success=True,
        session=session,
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    session_service = get_session_service()
    success = await session_service.delete_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"success": True, "message": "Session deleted"}


@router.delete("/sessions")
async def clear_all_sessions():
    """清空所有会话"""
    session_service = get_session_service()
    count = await session_service.clear_all_sessions()

    return {"success": True, "message": f"Cleared {count} sessions"}


@router.get("/modes")
async def list_modes():
    """获取可用的 Agent 模式"""
    return {
        "success": True,
        "modes": [
            {
                "value": "sequential",
                "label": "顺序执行",
                "description": "Agent 按顺序依次执行，适合需要依赖关系的复杂诊断流程",
            },
            {
                "value": "parallel",
                "label": "并行执行",
                "description": "所有 Agent 同时执行，适合快速查询和独立任务",
            },
            {
                "value": "hierarchical",
                "label": "层级执行",
                "description": "按层级顺序执行，先宏观分析再微观诊断",
            },
            {
                "value": "debate",
                "label": "辩论模式",
                "description": "多 Agent 辩论后选出最佳方案，适合争议性问题",
            },
        ]
    }


@router.post("/visualize")
async def visualize(request: dict):
    """生成可视化图表"""
    query = request.get("query", "")

    try:
        viz_service = AdvancedVisualizationService()
        result = await viz_service.visualize(query)

        return {
            "success": result.success,
            "chart_base64": result.chart_base64,
            "chart_html": result.chart_html,
            "title": result.title,
            "description": result.description,
            "error": result.error,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/visualize/examples")
async def get_visualize_examples():
    """获取可视化示例查询"""
    return {
        "success": True,
        "examples": [
            {"query": "画一个最近24小时的延迟趋势图", "type": "line"},
            {"query": "显示各区域流量对比柱状图", "type": "bar"},
            {"query": "查看错误率分布饼图", "type": "pie"},
            {"query": "最近7天的CPU使用率变化", "type": "line"},
        ]
    }


@router.post("/visualize/advanced")
async def advanced_visualize(request: dict):
    """高级可视化"""
    query = request.get("query", "")
    chart_type = request.get("chart_type", "auto")
    time_range = request.get("time_range", "24h")
    filters = request.get("filters", {})

    try:
        viz_service = AdvancedVisualizationService()
        result = await viz_service.visualize(
            query=query,
            chart_type=chart_type if chart_type != "auto" else None,
        )

        return {
            "success": result.success,
            "chart_base64": result.chart_base64,
            "chart_html": result.chart_html,
            "title": result.title,
            "description": result.description,
            "error": result.error,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
