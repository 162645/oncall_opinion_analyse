"""
Skill 管理模块
用户自定义技能系统
"""

from .models import (
    Skill,
    SkillTrigger,
    SkillStep,
    SkillParam,
    SkillScope,
    SkillStatus,
    SkillCategory,
    SkillExecution,
    SYSTEM_SKILLS,
)
from .service import SkillService, get_skill_service
from .executor import SkillExecutor
from .analyzer import FlowAnalyzer, SkillRecommendation
from .lifecycle import ReplayCase, ReplayReport, SkillLifecycleManager, SkillVersion

__all__ = [
    # 数据模型
    "Skill",
    "SkillTrigger",
    "SkillStep",
    "SkillParam",
    "SkillScope",
    "SkillStatus",
    "SkillCategory",
    "SkillExecution",
    # 预设 Skills
    "SYSTEM_SKILLS",
    # 服务
    "SkillService",
    "get_skill_service",
    # 执行器
    "SkillExecutor",
    # 分析器
    "FlowAnalyzer",
    "SkillRecommendation",
    "ReplayCase",
    "ReplayReport",
    "SkillLifecycleManager",
    "SkillVersion",
]
