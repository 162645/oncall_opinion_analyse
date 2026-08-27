"""
Skill 数据模型
定义用户自定义技能的数据结构
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class SkillScope(Enum):
    """Skill 作用域"""
    PERSONAL = "personal"    # 个人私有
    TEAM = "team"            # 团队共享
    SYSTEM = "system"        # 系统预设


class SkillStatus(Enum):
    """Skill 状态"""
    DRAFT = "draft"              # 草稿
    PENDING = "pending"          # 待审核
    ACTIVE = "active"            # 活跃
    DEPRECATED = "deprecated"    # 已弃用
    ARCHIVED = "archived"        # 已归档
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    APPROVED = "approved"
    PUBLISHED = "published"
    ROLLED_BACK = "rolled_back"


class SkillCategory(Enum):
    """Skill 分类"""
    DIAGNOSIS = "diagnosis"      # 故障诊断
    ANALYSIS = "analysis"        # 数据分析
    OPERATION = "operation"      # 运维操作
    VISUALIZATION = "visualization"  # 可视化
    CUSTOM = "custom"            # 自定义


@dataclass
class SkillTrigger:
    """
    Skill 触发条件

    定义何时触发这个 Skill
    """
    keywords: List[str] = field(default_factory=list)      # 关键词触发
    intent: Optional[str] = None                            # 意图触发
    entities: List[str] = field(default_factory=list)      # 实体触发
    pattern: Optional[str] = None                           # 正则模式

    def matches(self, query: str, intent: Optional[str] = None) -> bool:
        """检查是否匹配触发条件"""
        query_lower = query.lower()

        # 关键词匹配
        for keyword in self.keywords:
            if keyword.lower() in query_lower:
                return True

        # 意图匹配
        if self.intent and intent == self.intent:
            return True

        # 正则匹配
        if self.pattern:
            import re
            if re.search(self.pattern, query, re.IGNORECASE):
                return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keywords": self.keywords,
            "intent": self.intent,
            "entities": self.entities,
            "pattern": self.pattern,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillTrigger":
        return cls(
            keywords=data.get("keywords", []),
            intent=data.get("intent"),
            entities=data.get("entities", []),
            pattern=data.get("pattern"),
        )


@dataclass
class SkillParam:
    """
    Skill 参数定义

    定义 Skill 执行时需要的参数
    """
    name: str                                    # 参数名
    type: str                                    # 类型: string, number, enum, boolean
    description: str = ""                        # 描述
    default: Any = None                          # 默认值
    required: bool = True                        # 是否必填
    options: Optional[List[str]] = None          # 枚举选项

    def validate(self, value: Any) -> bool:
        """验证参数值"""
        if value is None:
            return not self.required

        if self.type == "string":
            return isinstance(value, str)
        elif self.type == "number":
            return isinstance(value, (int, float))
        elif self.type == "boolean":
            return isinstance(value, bool)
        elif self.type == "enum":
            return value in (self.options or [])

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "default": self.default,
            "required": self.required,
            "options": self.options,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillParam":
        return cls(
            name=data.get("name", ""),
            type=data.get("type", "string"),
            description=data.get("description", ""),
            default=data.get("default"),
            required=data.get("required", True),
            options=data.get("options"),
        )


@dataclass
class SkillStep:
    """
    Skill 执行步骤

    定义 Skill 工作流中的单个步骤
    """
    step_type: str                               # 类型: agent, tool, retrieval, condition
    name: str                                    # 步骤名称
    config: Dict[str, Any] = field(default_factory=dict)  # 配置
    condition: Optional[str] = None              # 执行条件
    on_failure: str = "continue"                 # 失败处理: continue, stop, retry

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_type": self.step_type,
            "name": self.name,
            "config": self.config,
            "condition": self.condition,
            "on_failure": self.on_failure,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillStep":
        return cls(
            step_type=data.get("step_type", "agent"),
            name=data.get("name", ""),
            config=data.get("config", {}),
            condition=data.get("condition"),
            on_failure=data.get("on_failure", "continue"),
        )


@dataclass
class Skill:
    """
    用户自定义技能

    封装可复用的诊断/分析/操作流程
    """
    # 基本信息
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: SkillCategory = SkillCategory.CUSTOM
    tags: List[str] = field(default_factory=list)

    # 所有权
    owner: str = ""
    scope: SkillScope = SkillScope.PERSONAL
    team_id: Optional[str] = None

    # 核心内容
    trigger: SkillTrigger = field(default_factory=SkillTrigger)
    workflow: List[SkillStep] = field(default_factory=list)
    parameters: List[SkillParam] = field(default_factory=list)

    # 统计
    success_count: int = 0
    failure_count: int = 0
    usage_count: int = 0
    rating: float = 0.0
    rating_count: int = 0

    # 版本和状态
    version: str = "1.0.0"
    status: SkillStatus = SkillStatus.DRAFT

    # 时间
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    @property
    def quality_score(self) -> float:
        """质量评分"""
        # 使用频率得分
        usage_score = min(self.usage_count / 100, 1.0)

        # 成功率得分
        success_score = self.success_rate

        # 用户评分
        rating_score = self.rating / 5.0 if self.rating_count > 0 else 0.5

        # 完整度得分
        completeness = self._completeness_score

        return (
            0.25 * usage_score +
            0.30 * success_score +
            0.25 * rating_score +
            0.20 * completeness
        )

    @property
    def _completeness_score(self) -> float:
        """完整度得分"""
        score = 0.0
        if self.description: score += 0.25
        if self.tags: score += 0.25
        if self.trigger.keywords: score += 0.25
        if len(self.workflow) >= 2: score += 0.25
        return score

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "tags": self.tags,
            "owner": self.owner,
            "scope": self.scope.value,
            "team_id": self.team_id,
            "trigger": self.trigger.to_dict(),
            "workflow": [s.to_dict() for s in self.workflow],
            "parameters": [p.to_dict() for p in self.parameters],
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "usage_count": self.usage_count,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "version": self.version,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "quality_score": self.quality_score,
            "success_rate": self.success_rate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        """从字典创建"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=SkillCategory(data.get("category", "custom")),
            tags=data.get("tags", []),
            owner=data.get("owner", ""),
            scope=SkillScope(data.get("scope", "personal")),
            team_id=data.get("team_id"),
            trigger=SkillTrigger.from_dict(data.get("trigger", {})),
            workflow=[SkillStep.from_dict(s) for s in data.get("workflow", [])],
            parameters=[SkillParam.from_dict(p) for p in data.get("parameters", [])],
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            usage_count=data.get("usage_count", 0),
            rating=data.get("rating", 0.0),
            rating_count=data.get("rating_count", 0),
            version=data.get("version", "1.0.0"),
            status=SkillStatus(data.get("status", "draft")),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
        )


@dataclass
class SkillExecution:
    """Skill 执行记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    skill_id: str = ""
    user_id: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    duration_ms: int = 0
    steps_executed: List[Dict[str, Any]] = field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None
    feedback_score: Optional[int] = None
    feedback_comment: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "user_id": self.user_id,
            "params": self.params,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "steps_executed": self.steps_executed,
            "result": self.result,
            "error": self.error,
            "feedback_score": self.feedback_score,
            "feedback_comment": self.feedback_comment,
            "executed_at": self.executed_at.isoformat(),
        }


# ===== 预设 System Skills =====
# 只包含网络分析项目实际使用的技能

SYSTEM_SKILLS: List[Dict[str, Any]] = [
    # ===== 网络测量数据分析 =====
    {
        "id": "skill-ping-analysis",
        "name": "Ping数据分析",
        "description": "分析 Ping 测量数据，计算 RTT 统计指标（平均、中位数、百分位数等），支持按 AS、国家、数据中心等维度分析",
        "category": "analysis",
        "tags": ["Ping", "RTT", "网络测量", "统计分析"],
        "scope": "system",
        "trigger": {
            "keywords": ["ping", "RTT", "延迟数据", "网络测量", "rtt统计", "ping分析", "延迟统计"],
            "intent": "analysis",
        },
        "workflow": [
            {
                "step_type": "tool",
                "name": "查询Ping统计",
                "config": {"tool": "network_viz", "action": "ping_overall"},
            },
        ],
        "parameters": [
            {"name": "region", "type": "string", "description": "地区名称（如 UKRAINE）", "required": True},
            {"name": "dimension", "type": "enum", "description": "分析维度", "required": False, "options": ["overall", "asn", "asgeo", "country", "data_center", "prefix24"]},
        ],
        "status": "active",
    },
    {
        "id": "skill-ping-trend",
        "name": "延迟趋势分析",
        "description": "分析 Ping 数据的时间趋势，查看 RTT 随时间的变化，支持小时/天粒度",
        "category": "analysis",
        "tags": ["Ping", "趋势", "时间序列", "可视化"],
        "scope": "system",
        "trigger": {
            "keywords": ["时间趋势", "趋势图", "延迟变化", "rtt趋势", "时间序列", "走势"],
            "intent": "analysis",
        },
        "workflow": [
            {
                "step_type": "tool",
                "name": "查询时间趋势",
                "config": {"tool": "network_viz", "action": "ping_trend"},
            },
        ],
        "parameters": [
            {"name": "region", "type": "string", "description": "地区名称", "required": True},
            {"name": "interval", "type": "enum", "description": "时间粒度", "required": False, "options": ["minute", "hour", "day"]},
        ],
        "status": "active",
    },
    {
        "id": "skill-traceroute-analysis",
        "name": "Traceroute路径分析",
        "description": "分析 Traceroute 路径数据，查看 AS 路径分布、末端节点、跳数统计等",
        "category": "analysis",
        "tags": ["Traceroute", "路径", "AS路径", "网络拓扑"],
        "scope": "system",
        "trigger": {
            "keywords": ["traceroute", "路由追踪", "路径分析", "AS路径", "跳数", "网络路径"],
            "intent": "network_viz",
        },
        "workflow": [
            {
                "step_type": "tool",
                "name": "分析Traceroute",
                "config": {"tool": "network_viz", "action": "trace_path_analysis"},
            },
        ],
        "parameters": [
            {"name": "region", "type": "string", "description": "地区名称", "required": True},
            {"name": "path_type", "type": "enum", "description": "路径类型", "required": False, "options": ["as", "asgeo"]},
        ],
        "status": "active",
    },
    {
        "id": "skill-terminal-analysis",
        "name": "末端节点分析",
        "description": "分析 Traceroute 数据中的末端节点分布，统计各末端 AS/ASGeo 的路径数量和 Prefix24 分布",
        "category": "analysis",
        "tags": ["Traceroute", "末端", "AS", "节点分析"],
        "scope": "system",
        "trigger": {
            "keywords": ["末端节点", "终端节点", "末端分析", "terminal", "末端 AS"],
            "intent": "network_viz",
        },
        "workflow": [
            {
                "step_type": "tool",
                "name": "分析末端节点",
                "config": {"tool": "network_viz", "action": "trace_terminal_analysis"},
            },
        ],
        "parameters": [
            {"name": "region", "type": "string", "description": "地区名称", "required": True},
            {"name": "path_type", "type": "enum", "description": "路径类型", "required": False, "options": ["as", "asgeo"]},
        ],
        "status": "active",
    },
    {
        "id": "skill-path-ping-trend",
        "name": "路径Ping时序分析",
        "description": "分析特定 AS/ASGeo 路径关联的所有末端节点的 Ping 数据时序趋势",
        "category": "analysis",
        "tags": ["路径", "Ping", "时序", "趋势", "关联分析"],
        "scope": "system",
        "trigger": {
            "keywords": ["路径 ping", "路径时序", "ping 时序", "路径关联 ping"],
            "intent": "network_viz",
        },
        "workflow": [
            {
                "step_type": "tool",
                "name": "分析路径 Ping 时序",
                "config": {"tool": "network_viz", "action": "trace_path_ping_trend"},
            },
        ],
        "parameters": [
            {"name": "region", "type": "string", "description": "地区名称", "required": True},
            {"name": "path", "type": "string", "description": "路径字符串", "required": True},
            {"name": "path_type", "type": "enum", "description": "路径类型", "required": False, "options": ["as", "asgeo"]},
            {"name": "interval", "type": "enum", "description": "时间间隔", "required": False, "options": ["minute", "hour", "day"]},
        ],
        "status": "active",
    },
    {
        "id": "skill-region-overview",
        "name": "地区网络概览",
        "description": "获取指定地区的网络测量数据概览，包括 Ping 统计、路径统计、数据源信息等",
        "category": "analysis",
        "tags": ["概览", "地区", "网络统计"],
        "scope": "system",
        "trigger": {
            "keywords": ["概览", "地区概览", "网络概览", "总览", "overview"],
            "intent": "network_viz",
        },
        "workflow": [
            {
                "step_type": "tool",
                "name": "获取地区概览",
                "config": {"tool": "network_viz", "action": "region_overview"},
            },
        ],
        "parameters": [
            {"name": "region", "type": "string", "description": "地区名称", "required": True},
        ],
        "status": "active",
    },
    # ===== 可视化 =====
    {
        "id": "skill-network-viz",
        "name": "网络可视化分析",
        "description": "在智能对话中进行 Traceroute 和 Ping 数据的可视化分析，支持末端节点分析、路径分析、Ping 时序分析等",
        "category": "visualization",
        "tags": ["网络", "可视化", "Traceroute", "Ping", "路径分析", "时序分析"],
        "scope": "system",
        "trigger": {
            "keywords": ["traceroute", "路径分析", "末端节点", "as路径", "网络路径", "ping趋势", "网络可视化"],
            "intent": "network_viz",
        },
        "workflow": [
            {
                "step_type": "tool",
                "name": "执行网络可视化分析",
                "config": {"tool": "network_viz"},
            },
        ],
        "parameters": [
            {"name": "action", "type": "enum", "description": "分析操作类型", "required": True, "options": ["ping_overall", "ping_trend", "ping_by_asn", "ping_by_asgeo", "trace_terminal_analysis", "trace_path_analysis", "trace_path_ping_trend", "region_overview"]},
            {"name": "region", "type": "string", "description": "地区名称", "required": True},
        ],
        "status": "active",
    },
]
