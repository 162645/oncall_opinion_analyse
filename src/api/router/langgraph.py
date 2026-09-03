"""
LangGraph API 路由
提供基于状态机的 Agent 执行接口
"""

from typing import Optional, List
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.harness import get_harness

router = APIRouter()


# ===== 请求/响应模型 =====

class ExecuteRequest(BaseModel):
    """执行请求"""
    query: str
    session_id: Optional[str] = None
    require_human_approval: bool = False


class StepInfo(BaseModel):
    """步骤信息"""
    step: str
    intent: Optional[str] = None
    decision: Optional[str] = None
    found: Optional[bool] = None
    tools_called: Optional[List[str]] = None
    confidence: Optional[float] = None


class ExecuteResponse(BaseModel):
    """执行响应"""
    success: bool
    response: str
    intent: str
    confidence: float
    steps: List[dict]
    error: Optional[str] = None
    interrupted: bool = False
    thread_id: str = ""


class ResumeRequest(BaseModel):
    thread_id: str
    approved: bool = True


class GraphInfo(BaseModel):
    """图信息"""
    nodes: List[str]
    description: str


# ===== API 端点 =====

@router.post("/execute", response_model=ExecuteResponse)
async def execute_graph(request: ExecuteRequest):
    """
    执行 Agent 图

    基于状态机的 Agent 执行流程:
    1. Router - 意图识别
    2. Knowledge - 知识检索 (可选)
    3. Tools - 工具调用 (可选)
    4. Reasoning - 推理分析
    5. Output - 生成响应
    """
    builder = get_harness()

    result = await builder.execute(
        query=request.query,
        session_id=request.session_id,
        metadata={"require_human_approval": request.require_human_approval},
    )

    return ExecuteResponse(
        success=result.success,
        response=result.message,
        intent=result.state.get("task", {}).get("kind", "unknown"),
        confidence=result.confidence,
        steps=result.trace,
        error=result.error,
        interrupted=False,
        thread_id=request.session_id or result.state.get("session_id", ""),
    )


@router.post("/resume", response_model=ExecuteResponse)
async def resume_graph(request: ResumeRequest):
    result = ExecuteResponse(success=False, response="当前 Harness 不包含破坏性工具的人审中断点，无需 resume。", intent="unknown", confidence=0.0, steps=[], error="RESUME_NOT_SUPPORTED", thread_id=request.thread_id)
    return result


@router.post("/stream")
async def stream_graph(request: ExecuteRequest):
    async def events():
        async for node, update in get_harness().astream(
            request.query,
            request.session_id,
            metadata={"require_human_approval": request.require_human_approval},
        ):
            yield json.dumps({"node": node, "update": update}, ensure_ascii=False, default=str) + "\n"
    return StreamingResponse(events(), media_type="application/x-ndjson")


@router.get("/info")
async def get_graph_info():
    """获取 Agent 图信息"""
    return {
        "success": True,
        "graph": {
            "name": "Oncall Evidence-Driven Harness",
            "version": "6.0.0",
            "nodes": list(get_harness().CORE_NODES),
            "routes": {
                "all": "understand → context → planner → executor → verifier → synthesizer",
                "replan": "verifier → planner (reserved for evidence gaps, bounded by max_rounds)",
            },
        },
    }


@router.get("/tools")
async def list_tools():
    """列出可用工具"""
    return {
        "success": True,
        "tools": [
            {"name": "ping.summary", "description": "整体 RTT 与 P95/P99"},
            {"name": "ping.trend", "description": "按小时 RTT 趋势"},
            {"name": "ping.by_asn", "description": "按 AS 的 RTT 对比"},
            {"name": "ping.by_prefix24", "description": "按 /24 前缀的 RTT 对比"},
            {"name": "ping.outliers", "description": "异常 RTT 样本"},
            {"name": "trace.paths", "description": "Traceroute 路径稳定性"},
            {"name": "trace.path_change", "description": "按小时的路径变化"},
        ],
    }
