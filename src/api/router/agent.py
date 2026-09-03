"""
Agent 管理 API
提供 Agent 配置和状态管理
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.tools.registry import get_registry

router = APIRouter()


# ===== 模型定义 =====

class AgentInfo(BaseModel):
    """Agent 信息"""
    id: str
    name: str
    role: str
    description: str
    tools: List[str]
    enabled: bool
    last_used: Optional[str] = None


class AgentListResponse(BaseModel):
    """Agent 列表响应"""
    success: bool
    agents: List[AgentInfo]


class ToolInfo(BaseModel):
    """工具信息"""
    id: str
    name: str
    description: str
    parameters: dict
    category: str
    tags: List[str]
    enabled: bool


class ToolListResponse(BaseModel):
    """工具列表响应"""
    success: bool
    tools: List[ToolInfo]
    total: int


# ===== Agent 定义 =====

_agents = [
    AgentInfo(
        id="knowledge_agent",
        name="知识检索 Agent",
        role="knowledge",
        description="从知识库检索历史案例和 SOP 文档",
        tools=["knowledge-search", "vector-search"],
        enabled=True,
    ),
    AgentInfo(
        id="analysis_agent",
        name="数据分析 Agent",
        role="analysis",
        description="分析网络测量数据，检测异常和趋势",
        tools=["ping_stats", "ping_trend", "traceroute_analysis", "anomaly_detection"],
        enabled=True,
    ),
    AgentInfo(
        id="diagnosis_agent",
        name="诊断 Agent",
        role="diagnosis",
        description="综合分析生成诊断结论和建议",
        tools=["drill_down_analysis", "correlation_analysis", "create_visualization"],
        enabled=True,
    ),
    AgentInfo(
        id="visualization_agent",
        name="可视化 Agent",
        role="visualization",
        description="生成数据可视化图表",
        tools=["create_visualization", "ping_stats", "ping_trend"],
        enabled=True,
    ),
]


# ===== API 端点 =====

@router.get("/list", response_model=AgentListResponse)
async def list_agents():
    """获取 Agent 列表"""
    return AgentListResponse(
        success=True,
        agents=_agents,
    )


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """获取 Agent 详情"""
    for agent in _agents:
        if agent.id == agent_id:
            return {"success": True, "agent": agent}

    raise HTTPException(status_code=404, detail="Agent not found")


@router.post("/{agent_id}/toggle")
async def toggle_agent(agent_id: str, enabled: bool):
    """启用/禁用 Agent"""
    for agent in _agents:
        if agent.id == agent_id:
            agent.enabled = enabled
            return {"success": True, "agent": agent, "enabled": enabled}

    raise HTTPException(status_code=404, detail="Agent not found")


@router.get("/tools/list", response_model=ToolListResponse)
async def list_tools():
    """获取工具列表（从工具注册中心）"""
    registry = get_registry()
    tools_metadata = registry.list_all()

    tools = []
    for meta in tools_metadata:
        tools.append(ToolInfo(
            id=meta.name,
            name=meta.name,
            description=meta.description,
            parameters=meta.parameters,
            category=meta.category.value if hasattr(meta.category, 'value') else str(meta.category),
            tags=meta.tags or [],
            enabled=not meta.deprecated,
        ))

    return ToolListResponse(
        success=True,
        tools=tools,
        total=len(tools),
    )


@router.get("/status")
async def get_agent_status():
    """获取 Agent 系统状态"""
    return {
        "success": True,
        "status": {
            "total_agents": len(_agents),
            "enabled_agents": len([a for a in _agents if a.enabled]),
            "total_tools": len(_tools),
            "orchestrator": "running",
            "last_updated": datetime.now().isoformat(),
        },
    }


@router.get("/modes/recommend")
async def recommend_mode(query: str):
    """
    根据查询推荐 Agent 模式

    自动选择最适合的执行模式
    """
    # 简单的关键词匹配
    query_lower = query.lower()

    if any(kw in query_lower for kw in ["快速", "简单", "查询", "quick", "simple"]):
        recommended = "parallel"
        reason = "简单查询适合并行快速处理"
    elif any(kw in query_lower for kw in ["诊断", "分析", "根因", "diagnose", "root cause"]):
        recommended = "sequential"
        reason = "复杂诊断适合顺序逐步分析"
    elif any(kw in query_lower for kw in ["对比", "哪个更好", "compare", "which is better"]):
        recommended = "debate"
        reason = "需要多角度对比分析"
    else:
        recommended = "sequential"
        reason = "默认顺序模式"

    return {
        "success": True,
        "recommended_mode": recommended,
        "reason": reason,
        "query": query,
    }
