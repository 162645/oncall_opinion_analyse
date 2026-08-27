"""
Skill API 路由
提供 Skill 管理和执行的 REST API
"""

import json
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.skill import (
    Skill,
    SkillService,
    get_skill_service,
    SkillExecutor,
    FlowAnalyzer,
    SkillRecommendation,
    SYSTEM_SKILLS,
)
from src.skill.extractor import SkillExtractor, get_skill_extractor
from src.skill.matcher import SkillMatcher, get_skill_matcher

router = APIRouter()


# ===== 请求/响应模型 =====

class CreateSkillRequest(BaseModel):
    """创建 Skill 请求"""
    name: str
    description: str
    workflow: List[dict]
    trigger: Optional[dict] = None
    parameters: Optional[List[dict]] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = "custom"
    scope: Optional[str] = "personal"
    team_id: Optional[str] = None


class UpdateSkillRequest(BaseModel):
    """更新 Skill 请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    workflow: Optional[List[dict]] = None
    trigger: Optional[dict] = None
    parameters: Optional[List[dict]] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class ExecuteSkillRequest(BaseModel):
    """执行 Skill 请求"""
    params: dict
    context: Optional[dict] = None


class SearchSkillRequest(BaseModel):
    """搜索 Skill 请求"""
    query: str
    top_k: Optional[int] = 10


class RecordFeedbackRequest(BaseModel):
    """记录反馈请求"""
    score: int  # 1-5
    comment: Optional[str] = None


class SkillResponse(BaseModel):
    """Skill 响应"""
    success: bool
    skill: Optional[dict] = None
    error: Optional[str] = None


class SkillListResponse(BaseModel):
    """Skill 列表响应"""
    success: bool
    total: int
    page: int
    page_size: int
    skills: List[dict]


class ExecutionResponse(BaseModel):
    """执行响应"""
    success: bool
    execution_id: str
    skill_id: str
    result: Optional[str] = None
    steps_executed: List[dict]
    duration_ms: int
    error: Optional[str] = None


# ===== API 端点 =====

@router.post("/", response_model=SkillResponse)
async def create_skill(request: CreateSkillRequest):
    """
    创建 Skill

    创建一个新的自定义技能

    - **name**: Skill 名称
    - **description**: 描述
    - **workflow**: 执行步骤列表
    - **scope**: 作用域 (personal/team/system)
    """
    service = get_skill_service()

    # TODO: 从认证获取 user_id
    user_id = "user_default"

    try:
        skill = await service.create(
            name=request.name,
            description=request.description,
            owner=user_id,
            workflow=request.workflow,
            trigger=request.trigger,
            parameters=request.parameters,
            tags=request.tags,
            category=request.category,
            scope=request.scope,
            team_id=request.team_id,
        )

        return SkillResponse(
            success=True,
            skill=skill.to_dict(),
        )

    except Exception as e:
        return SkillResponse(
            success=False,
            error=str(e),
        )


@router.get("/", response_model=SkillListResponse)
async def list_skills(
    scope: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    min_rating: Optional[float] = None,
    sort_by: Optional[str] = "usage",
    page: int = 1,
    page_size: int = 20,
):
    """
    列出 Skill

    获取可见的 Skill 列表，支持过滤和排序

    - **scope**: 作用域过滤 (personal/team/system)
    - **category**: 分类过滤
    - **sort_by**: 排序方式 (usage/rating/quality/created)
    """
    service = get_skill_service()
    user_id = "user_default"  # TODO: 从认证获取
    team_id = None  # TODO: 从用户信息获取

    result = await service.list_skills(
        user_id=user_id,
        team_id=team_id,
        scope=scope,
        category=category,
        status=status,
        min_rating=min_rating,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )

    return SkillListResponse(
        success=True,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        skills=result["skills"],
    )


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: str):
    """获取 Skill 详情"""
    service = get_skill_service()
    skill = await service.get(skill_id)

    if not skill:
        return SkillResponse(
            success=False,
            error=f"Skill not found: {skill_id}",
        )

    return SkillResponse(
        success=True,
        skill=skill.to_dict(),
    )


@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(skill_id: str, request: UpdateSkillRequest):
    """更新 Skill"""
    service = get_skill_service()

    updates = {}
    if request.name:
        updates["name"] = request.name
    if request.description:
        updates["description"] = request.description
    if request.workflow:
        updates["workflow"] = request.workflow
    if request.trigger:
        updates["trigger"] = request.trigger
    if request.parameters:
        updates["parameters"] = request.parameters
    if request.tags:
        updates["tags"] = request.tags
    if request.status:
        updates["status"] = request.status

    skill = await service.update(skill_id, **updates)

    if not skill:
        return SkillResponse(
            success=False,
            error=f"Skill not found: {skill_id}",
        )

    return SkillResponse(
        success=True,
        skill=skill.to_dict(),
    )


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str):
    """删除 Skill"""
    service = get_skill_service()
    success = await service.delete(skill_id)

    if not success:
        raise HTTPException(status_code=404, detail="Skill not found or cannot be deleted")

    return {"success": True, "message": "Skill deleted"}


@router.post("/search")
async def search_skills(request: SearchSkillRequest):
    """
    搜索 Skill

    根据关键词搜索匹配的 Skill
    """
    service = get_skill_service()
    user_id = "user_default"
    team_id = None

    results = await service.search(
        query=request.query,
        user_id=user_id,
        team_id=team_id,
        top_k=request.top_k,
    )

    return {
        "success": True,
        "query": request.query,
        "results": [
            {
                "skill": r.skill.to_dict(),
                "score": r.score,
                "match_reason": r.match_reason,
            }
            for r in results
        ],
    }


@router.post("/recommend")
async def recommend_skills():
    """
    推荐 Skill

    根据用户查询推荐匹配的 Skill
    """
    # TODO: 从请求获取 query 和 intent
    return {
        "success": True,
        "message": "Use /search for now",
    }


@router.post("/{skill_id}/execute", response_model=ExecutionResponse)
async def execute_skill(skill_id: str, request: ExecuteSkillRequest):
    """
    执行 Skill

    使用给定参数执行一个 Skill
    """
    service = get_skill_service()
    skill = await service.get(skill_id)

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # 执行
    executor = SkillExecutor()
    execution = await executor.execute(
        skill=skill,
        params=request.params,
        context=request.context,
    )

    # 记录执行
    await service.record_execution(
        skill_id=skill_id,
        user_id=request.context.get("user_id", "") if request.context else "",
        params=request.params,
        success=execution.success,
        duration_ms=execution.duration_ms,
        result=execution.result,
        error=execution.error,
    )

    return ExecutionResponse(
        success=execution.success,
        execution_id=execution.id,
        skill_id=skill_id,
        result=execution.result,
        steps_executed=execution.steps_executed,
        duration_ms=execution.duration_ms,
        error=execution.error,
    )


@router.post("/{skill_id}/rate")
async def rate_skill(skill_id: str, request: RecordFeedbackRequest):
    """
    评价 Skill

    为执行过的 Skill 提供反馈
    """
    # TODO: 需要关联到具体的执行记录
    service = get_skill_service()
    skill = await service.get(skill_id)

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # 更新评分
    # 这里简化处理，直接更新
    await service.update(skill_id, rating=request.score)

    return {
        "success": True,
        "message": "Feedback recorded",
    }


@router.post("/{skill_id}/deprecate")
async def deprecate_skill(skill_id: str, reason: Optional[str] = None):
    """弃用 Skill"""
    service = get_skill_service()
    success = await service.deprecate(skill_id, reason or "")

    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")

    return {"success": True, "message": "Skill deprecated"}


@router.post("/{skill_id}/archive")
async def archive_skill(skill_id: str):
    """归档 Skill"""
    service = get_skill_service()
    success = await service.archive(skill_id)

    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")

    return {"success": True, "message": "Skill archived"}


@router.post("/{skill_id}/approve")
async def approve_skill(skill_id: str):
    """审核通过 Skill (团队 Skill)"""
    service = get_skill_service()
    success = await service.approve(skill_id)

    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")

    return {"success": True, "message": "Skill approved"}


@router.post("/{skill_id}/clone")
async def clone_skill(skill_id: str):
    """克隆 Skill"""
    service = get_skill_service()
    original = await service.get(skill_id)

    if not original:
        raise HTTPException(status_code=404, detail="Skill not found")

    # 创建副本
    user_id = "user_default"
    cloned = await service.create(
        name=f"{original.name} (副本)",
        description=original.description,
        owner=user_id,
        workflow=[s.to_dict() for s in original.workflow],
        trigger=original.trigger.to_dict(),
        parameters=[p.to_dict() for p in original.parameters],
        tags=original.tags.copy(),
        category=original.category.value,
        scope="personal",
    )

    return {
        "success": True,
        "original_id": skill_id,
        "cloned_skill": cloned.to_dict(),
    }


@router.get("/stats/overview")
async def get_skill_stats():
    """获取 Skill 统计概览"""
    service = get_skill_service()
    user_id = "user_default"

    stats = await service.get_stats(user_id)

    # 添加内置 skills 统计
    from pathlib import Path
    skills_dir = Path(__file__).parent.parent.parent.parent / ".claude" / "skills"

    # 网络分析项目实际使用的 skills
    project_skills = [
        "network-viz", "argos-query", "argos-alarm", "argos-dashboard",
        "metrics", "bytees", "aeolus", "diag",
    ]
    builtin_count = len([d for d in skills_dir.iterdir() if d.is_dir() and d.name in project_skills and (d / "SKILL.md").exists()])

    # 系统预设 skills
    system_skills_count = len(SYSTEM_SKILLS)

    stats["builtin_skills"] = builtin_count
    stats["system_skills"] = system_skills_count
    stats["total"] = stats.get("total", 0) + builtin_count + system_skills_count
    stats["system_count"] = stats.get("system_count", 0) + system_skills_count

    return {
        "success": True,
        "stats": stats,
    }


@router.get("/builtin/list")
async def list_builtin_skills():
    """
    列出网络分析项目相关的内置 Skills

    只返回本项目实际使用的 skills，不包括 TTADK 开发框架的 skills
    """
    from pathlib import Path
    import re

    skills_dir = Path(__file__).parent.parent.parent.parent / ".claude" / "skills"

    if not skills_dir.exists():
        return {"success": False, "error": "Skills directory not found", "skills": []}

    # 网络分析项目实际使用的 skills
    project_skills = [
        "network-viz",      # 网络可视化
        "argos-query",      # 日志查询
        "argos-alarm",      # 告警管理
        "argos-dashboard",  # 仪表盘
        "metrics",          # 指标查询
        "bytees",           # ES 查询
        "aeolus",           # BI 分析
        "diag",             # 诊断
        "neptune-acl",      # Neptune 访问控制
        "neptune-stability", # Neptune 稳定性
    ]

    skills = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue

        # 只加载项目相关的 skills
        if skill_dir.name not in project_skills:
            continue

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        try:
            content = skill_file.read_text(encoding="utf-8")

            # 解析 frontmatter
            name = skill_dir.name
            description = ""

            # 提取 YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = parts[1]
                    # 提取 name
                    name_match = re.search(r'^name:\s*(.+)$', frontmatter, re.MULTILINE)
                    if name_match:
                        name = name_match.group(1).strip().strip('"').strip("'")
                    # 提取 description
                    desc_match = re.search(r'^description:\s*(.+)$', frontmatter, re.MULTILINE)
                    if desc_match:
                        description = desc_match.group(1).strip().strip('"').strip("'")

            # 如果没有从 frontmatter 获取到描述，从内容中提取
            if not description:
                lines = content.split("\n")
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("---") and not line.startswith("name:") and not line.startswith("description:"):
                        description = line[:100]
                        break

            skills.append({
                "id": f"builtin-{skill_dir.name}",
                "name": name,
                "folder": skill_dir.name,
                "description": description[:200] if description else "",
                "scope": "builtin",
                "category": "network-analysis",
                "source": ".claude/skills",
            })
        except Exception as e:
            skills.append({
                "id": f"builtin-{skill_dir.name}",
                "name": skill_dir.name,
                "folder": skill_dir.name,
                "description": f"Error reading skill: {str(e)}",
                "scope": "builtin",
                "category": "network-analysis",
                "source": ".claude/skills",
            })

    return {
        "success": True,
        "total": len(skills),
        "skills": skills,
    }


@router.get("/system/list")
async def list_system_skills():
    """
    列出系统预设的 Skills

    返回 SYSTEM_SKILLS 中定义的网络分析相关技能
    """
    skills = []
    for skill_data in SYSTEM_SKILLS:
        # 计算质量评分
        usage_count = skill_data.get("usage_count", 0)
        success_count = skill_data.get("success_count", 0)
        failure_count = skill_data.get("failure_count", 0)
        rating = skill_data.get("rating", 0.0)
        rating_count = skill_data.get("rating_count", 0)

        total = success_count + failure_count
        success_rate = success_count / total if total > 0 else 0.0
        rating_score = rating / 5.0 if rating_count > 0 else 0.5

        # 完整度得分
        completeness = 0.0
        if skill_data.get("description"): completeness += 0.25
        if skill_data.get("tags"): completeness += 0.25
        trigger = skill_data.get("trigger", {})
        if trigger.get("keywords"): completeness += 0.25
        if len(skill_data.get("workflow", [])) >= 1: completeness += 0.25

        quality_score = (
            0.25 * min(usage_count / 100, 1.0) +
            0.30 * success_rate +
            0.25 * rating_score +
            0.20 * completeness
        )

        skills.append({
            **skill_data,
            "quality_score": quality_score,
            "success_rate": success_rate,
        })

    return {
        "success": True,
        "total": len(skills),
        "skills": skills,
    }


@router.get("/tools/list")
async def list_all_tools():
    """
    列出所有可用工具

    包括：
    1. src/tools/plugins/ 下的工具
    2. MCP 工具
    """
    from src.tools.registry import get_registry

    tools = []

    # 获取注册的工具
    try:
        registry = get_registry()
        for tool_meta in registry.list_all():
            tools.append({
                "name": tool_meta.name,
                "description": tool_meta.description,
                "category": tool_meta.category.value,
                "source": "plugins",
                "parameters": tool_meta.parameters,
            })
    except Exception as e:
        pass

    # 添加静态工具列表
    static_tools = [
        {
            "name": "clickhouse_query",
            "description": "查询网络测量数据（Ping、Traceroute）",
            "category": "database",
            "source": "plugins",
        },
        {
            "name": "ping_analysis",
            "description": "分析 Ping 数据，计算 RTT 统计指标",
            "category": "analysis",
            "source": "plugins",
        },
        {
            "name": "trace_analysis",
            "description": "分析 Traceroute 数据，提取路径信息",
            "category": "analysis",
            "source": "plugins",
        },
        {
            "name": "network_viz",
            "description": "网络可视化工具，支持 Traceroute/Ping 可视化分析",
            "category": "network",
            "source": "plugins",
        },
        {
            "name": "analyze_ping_data",
            "description": "分析网络 Ping 测量数据，支持多维度统计",
            "category": "analysis",
            "source": "mcp",
        },
        {
            "name": "analyze_traceroute_data",
            "description": "分析网络 Traceroute 路径数据",
            "category": "analysis",
            "source": "mcp",
        },
        {
            "name": "hierarchical_analysis",
            "description": "分层分析网络测量数据，支持逐层下钻",
            "category": "analysis",
            "source": "mcp",
        },
        {
            "name": "get_network_metadata",
            "description": "查询网络测量元数据",
            "category": "query",
            "source": "mcp",
        },
    ]

    # 合并去重
    existing_names = {t["name"] for t in tools}
    for tool in static_tools:
        if tool["name"] not in existing_names:
            tools.append(tool)

    return {
        "success": True,
        "total": len(tools),
        "tools": tools,
    }


# ===== 从执行创建 Skill =====

class FromExecutionRequest(BaseModel):
    """从执行创建 Skill 请求"""
    execution_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[str] = "personal"


@router.post("/from-execution")
async def create_from_execution(request: FromExecutionRequest):
    """
    从执行记录创建 Skill

    将一个成功的执行流程保存为可复用的 Skill
    """
    # TODO: 获取执行记录
    # 这里使用 FlowAnalyzer 进行分析

    return {
        "success": False,
        "error": "Execution not found",
        "message": "This feature requires execution history integration",
    }


@router.post("/analyze-flow")
async def analyze_flow(request: dict):
    """
    分析流程

    分析一个执行流程，判断是否值得保存为 Skill
    """
    from src.skill.analyzer import ExecutionTrace, get_flow_analyzer

    analyzer = get_flow_analyzer()

    # 构建执行轨迹
    trace = ExecutionTrace(
        session_id=request.get("session_id", ""),
        query=request.get("query", ""),
        intent=request.get("intent", "query"),
        steps=request.get("steps", []),
        success=request.get("success", True),
        duration_ms=request.get("duration_ms", 0),
        user_feedback=request.get("user_feedback"),
    )

    # 分析
    recommendation = await analyzer.analyze(trace)

    return {
        "success": True,
        "recommendation": {
            "recommended": recommendation.recommended,
            "reason": recommendation.reason,
            "suggested_name": recommendation.suggested_name,
            "suggested_description": recommendation.suggested_description,
            "suggested_workflow": recommendation.suggested_workflow,
            "suggested_trigger": recommendation.suggested_trigger,
            "suggested_params": recommendation.suggested_params,
            "confidence": recommendation.confidence,
        },
    }


# ===== Skill 提取 =====

class ExtractSkillRequest(BaseModel):
    """从对话提取 Skill 请求"""
    messages: List[dict]
    tool_calls: Optional[List[dict]] = None
    trace: Optional[List[dict]] = None
    result: Optional[dict] = None
    name: Optional[str] = None  # 覆盖名称


class ExtractSkillResponse(BaseModel):
    """提取 Skill 响应"""
    success: bool
    can_extract: bool
    skill: Optional[dict] = None
    extraction_result: Optional[dict] = None
    error: Optional[str] = None


class MatchSkillRequest(BaseModel):
    """匹配 Skill 请求"""
    query: str
    intent: Optional[str] = None
    entities: Optional[dict] = None
    top_k: Optional[int] = 5


@router.post("/extract", response_model=ExtractSkillResponse)
async def extract_skill(request: ExtractSkillRequest):
    """
    从对话中提取 Skill

    分析成功的对话，尝试提取可复用的技能

    - **messages**: 对话消息列表
    - **tool_calls**: 工具调用列表（可选）
    - **trace**: 执行追踪（可选）
    - **result**: 执行结果（可选）
    - **name**: 覆盖 Skill 名称（可选）
    """
    extractor = get_skill_extractor()
    user_id = "user_default"  # TODO: 从认证获取

    try:
        # 分析对话
        extraction_result = await extractor.analyze_conversation(
            messages=request.messages,
            tool_calls=request.tool_calls or [],
            trace=request.trace or [],
            result=request.result or {},
        )

        if not extraction_result.can_extract:
            return ExtractSkillResponse(
                success=True,
                can_extract=False,
                extraction_result={
                    "can_extract": False,
                    "reason": extraction_result.reason,
                },
            )

        # 创建 Skill
        skill = await extractor.extract_and_create(
            messages=request.messages,
            tool_calls=request.tool_calls or [],
            trace=request.trace or [],
            result=request.result or {},
            owner=user_id,
            name_override=request.name,
        )

        if skill:
            return ExtractSkillResponse(
                success=True,
                can_extract=True,
                skill=skill.to_dict(),
                extraction_result={
                    "can_extract": True,
                    "skill_name": extraction_result.skill_name,
                    "description": extraction_result.description,
                    "category": extraction_result.category,
                    "tags": extraction_result.tags,
                    "trigger_keywords": extraction_result.trigger_keywords,
                    "confidence": extraction_result.confidence,
                },
            )
        else:
            return ExtractSkillResponse(
                success=True,
                can_extract=True,
                extraction_result={
                    "can_extract": True,
                    "reason": "Similar skill already exists",
                    "skill_name": extraction_result.skill_name,
                },
            )

    except Exception as e:
        return ExtractSkillResponse(
            success=False,
            can_extract=False,
            error=str(e),
        )


@router.post("/match")
async def match_skill(request: MatchSkillRequest):
    """
    匹配 Skill

    将用户查询匹配到已有的 Skill

    - **query**: 用户查询
    - **intent**: 识别的意图（可选）
    - **entities**: 提取的实体（可选）
    - **top_k**: 返回数量
    """
    matcher = get_skill_matcher()
    user_id = "user_default"
    team_id = None

    results = await matcher.match(
        query=request.query,
        intent=request.intent,
        entities=request.entities,
        user_id=user_id,
        team_id=team_id,
        top_k=request.top_k,
    )

    return {
        "success": True,
        "query": request.query,
        "matches": [
            {
                "skill_id": r.skill.id,
                "skill_name": r.skill.name,
                "description": r.skill.description,
                "score": r.score,
                "match_type": r.match_type,
                "matched_terms": r.matched_terms,
                "extracted_params": r.params,
            }
            for r in results
        ],
    }


@router.post("/recommend")
async def recommend_skill(request: MatchSkillRequest):
    """
    推荐 Skill

    获取更详细的 Skill 推荐信息

    - **query**: 用户查询
    - **intent**: 识别的意图（可选）
    """
    matcher = get_skill_matcher()
    user_id = "user_default"

    recommendation = await matcher.get_skill_recommendation(
        query=request.query,
        intent=request.intent,
        user_id=user_id,
    )

    return {
        "success": True,
        **recommendation,
    }


@router.post("/suggest-create")
async def suggest_skill_creation(request: dict):
    """
    建议创建 Skill

    根据用户查询模式，建议可能需要的 Skill

    - **query**: 用户查询
    """
    extractor = get_skill_extractor()
    user_id = "user_default"

    suggestions = await extractor.suggest_skill_from_query(
        query=request.get("query", ""),
        user_id=user_id,
    )

    return {
        "success": True,
        "suggestions": suggestions,
    }


# ===== 用户自定义 Skill 文件存储 =====

USER_SKILLS_FILE = Path(__file__).parent.parent.parent.parent / "data" / "user_skills.json"


def _load_user_skills() -> List[dict]:
    """从文件加载用户 Skills"""
    if USER_SKILLS_FILE.exists():
        with open(USER_SKILLS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_user_skills(skills: List[dict]):
    """保存用户 Skills 到文件"""
    USER_SKILLS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_SKILLS_FILE, "w", encoding="utf-8") as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)


@router.post("/user/create")
async def create_user_skill(request: dict):
    """
    创建用户自定义 Skill（保存到文件）

    这是简化版的 Skill 创建，用于前端直接创建可执行的 Skill
    """
    import time

    skill_data = {
        "id": request.get("id") or f"user-skill-{int(time.time() * 1000)}",
        "name": request.get("name", ""),
        "description": request.get("description", ""),
        "category": request.get("category", "custom"),
        "tags": request.get("tags", []),
        "trigger": request.get("trigger", {}),
        "workflow": request.get("workflow", []),
        "parameters": request.get("parameters", []),
        "source": "user",
        "created_at": time.time(),
    }

    skills = _load_user_skills()

    # 检查是否已存在（更新）
    existing_idx = None
    for i, s in enumerate(skills):
        if s.get("id") == skill_data["id"]:
            existing_idx = i
            break

    if existing_idx is not None:
        skills[existing_idx] = skill_data
    else:
        skills.append(skill_data)

    _save_user_skills(skills)

    return {"success": True, "skill": skill_data}


@router.get("/user/list")
async def list_user_skills():
    """列出所有用户自定义 Skills"""
    skills = _load_user_skills()
    return {"success": True, "total": len(skills), "skills": skills}


@router.delete("/user/{skill_id}")
async def delete_user_skill(skill_id: str):
    """删除用户自定义 Skill"""
    skills = _load_user_skills()
    skills = [s for s in skills if s.get("id") != skill_id]
    _save_user_skills(skills)
    return {"success": True, "message": f"Skill {skill_id} deleted"}
