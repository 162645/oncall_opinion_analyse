"""
LangGraph API 路由
提供基于状态机的 Agent 执行接口
"""

from typing import Optional, List
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agents.langgraph import AgentGraphBuilder, get_graph_builder

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
    builder = get_graph_builder()

    result = await builder.execute(
        query=request.query,
        session_id=request.session_id,
        metadata={"require_human_approval": request.require_human_approval},
    )

    return ExecuteResponse(
        success=result.success,
        response=result.response,
        intent=result.intent,
        confidence=result.confidence,
        steps=result.steps,
        error=result.error,
        interrupted=result.interrupted,
        thread_id=result.thread_id,
    )


@router.post("/resume", response_model=ExecuteResponse)
async def resume_graph(request: ResumeRequest):
    result = await get_graph_builder().resume(request.thread_id, request.approved)
    return ExecuteResponse(
        success=result.success, response=result.response, intent=result.intent,
        confidence=result.confidence, steps=result.steps, error=result.error,
        interrupted=result.interrupted, thread_id=result.thread_id,
    )


@router.post("/stream")
async def stream_graph(request: ExecuteRequest):
    async def events():
        async for node, update in get_graph_builder().astream(
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
            "name": "Oncall Diagnosis Agent",
            "version": "5.0.0",
            "nodes": list(AgentGraphBuilder.CORE_NODES),
            "routes": {
                "query": "knowledge → reasoning ⇄ reflection → output",
                "diagnosis": "knowledge → tools → [human approval] → reasoning ⇄ reflection → output",
                "action": "tools → [human approval] → reasoning ⇄ reflection → output",
                "visualization": "output (direct)",
                "analysis": "knowledge → tools → reasoning ⇄ reflection → output",
            },
        },
    }


@router.get("/tools")
async def list_tools():
    """列出可用工具"""
    from src.agents.langgraph.nodes.tool_node import ToolNode

    tool_node = ToolNode()
    tools = tool_node.list_tools()

    return {
        "success": True,
        "tools": tools,
    }
