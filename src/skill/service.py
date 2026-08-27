"""
Skill 服务
管理 Skill 的存储、检索、生命周期
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging
import json
from datetime import datetime

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

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜索结果"""
    skill: Skill
    score: float
    match_reason: str


class SkillService:
    """
    Skill 管理服务

    功能:
    1. CRUD 操作
    2. 搜索和推荐
    3. 生命周期管理
    4. 质量评分
    5. 相似检测
    """

    def __init__(self):
        # 内存存储 (生产环境用数据库)
        self._skills: Dict[str, Skill] = {}
        self._executions: Dict[str, SkillExecution] = {}
        self._user_skills: Dict[str, List[str]] = {}  # user_id -> skill_ids
        self._team_skills: Dict[str, List[str]] = {}  # team_id -> skill_ids

        # 初始化系统预设 Skill
        self._init_system_skills()

    def _init_system_skills(self):
        """初始化系统预设 Skill"""
        for skill_data in SYSTEM_SKILLS:
            skill = Skill.from_dict(skill_data)
            self._skills[skill.id] = skill
        logger.info(f"Loaded {len(SYSTEM_SKILLS)} system skills")

    # ===== CRUD 操作 =====

    async def create(
        self,
        name: str,
        description: str,
        owner: str,
        workflow: List[Dict[str, Any]],
        trigger: Optional[Dict[str, Any]] = None,
        parameters: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
        category: str = "custom",
        scope: str = "personal",
        team_id: Optional[str] = None,
    ) -> Skill:
        """
        创建 Skill

        Args:
            name: Skill 名称
            description: 描述
            owner: 创建者
            workflow: 工作流步骤
            trigger: 触发条件
            parameters: 参数定义
            tags: 标签
            category: 分类
            scope: 作用域
            team_id: 团队ID

        Returns:
            创建的 Skill
        """
        # 检查相似 Skill
        similar = await self.find_similar(name, description)
        if similar and similar[0].score > 0.85:
            logger.warning(f"Similar skill exists: {similar[0].skill.name}")

        skill = Skill(
            name=name,
            description=description,
            owner=owner,
            category=SkillCategory(category),
            scope=SkillScope(scope),
            team_id=team_id,
            tags=tags or [],
            trigger=SkillTrigger.from_dict(trigger or {}),
            workflow=[SkillStep.from_dict(s) for s in workflow],
            parameters=[SkillParam.from_dict(p) for p in (parameters or [])],
            status=SkillStatus.DRAFT if scope == "team" else SkillStatus.ACTIVE,
        )

        # 存储
        self._skills[skill.id] = skill

        # 索引
        if scope == "personal":
            if owner not in self._user_skills:
                self._user_skills[owner] = []
            self._user_skills[owner].append(skill.id)
        elif scope == "team" and team_id:
            if team_id not in self._team_skills:
                self._team_skills[team_id] = []
            self._team_skills[team_id].append(skill.id)

        logger.info(f"Created skill: {skill.name} (id={skill.id})")
        return skill

    async def get(self, skill_id: str) -> Optional[Skill]:
        """获取 Skill"""
        return self._skills.get(skill_id)

    async def update(
        self,
        skill_id: str,
        **updates,
    ) -> Optional[Skill]:
        """更新 Skill"""
        skill = self._skills.get(skill_id)
        if not skill:
            return None

        # 更新字段
        if "name" in updates:
            skill.name = updates["name"]
        if "description" in updates:
            skill.description = updates["description"]
        if "tags" in updates:
            skill.tags = updates["tags"]
        if "workflow" in updates:
            skill.workflow = [SkillStep.from_dict(s) for s in updates["workflow"]]
        if "trigger" in updates:
            skill.trigger = SkillTrigger.from_dict(updates["trigger"])
        if "parameters" in updates:
            skill.parameters = [SkillParam.from_dict(p) for p in updates["parameters"]]
        if "status" in updates:
            skill.status = SkillStatus(updates["status"])

        skill.updated_at = datetime.now()
        skill.version = self._increment_version(skill.version)

        return skill

    async def delete(self, skill_id: str) -> bool:
        """删除 Skill"""
        skill = self._skills.get(skill_id)
        if not skill:
            return False

        # 系统预设不可删除
        if skill.scope == SkillScope.SYSTEM:
            logger.warning(f"Cannot delete system skill: {skill_id}")
            return False

        # 从索引移除
        if skill.scope == SkillScope.PERSONAL:
            if skill.owner in self._user_skills:
                self._user_skills[skill.owner].remove(skill_id)
        elif skill.scope == SkillScope.TEAM and skill.team_id:
            if skill.team_id in self._team_skills:
                self._team_skills[skill.team_id].remove(skill_id)

        del self._skills[skill_id]
        return True

    # ===== 查询操作 =====

    async def list_skills(
        self,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
        scope: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        min_rating: Optional[float] = None,
        sort_by: str = "usage",
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        列出 Skill

        Args:
            user_id: 用户ID (用于个人 Skill)
            team_id: 团队ID (用于团队 Skill)
            scope: 作用域过滤
            category: 分类过滤
            status: 状态过滤
            min_rating: 最低评分
            sort_by: 排序方式 (usage, rating, quality, created)

        Returns:
            分页结果
        """
        # 收集候选
        candidates = []

        # 系统预设
        for skill in self._skills.values():
            if skill.scope == SkillScope.SYSTEM:
                candidates.append(skill)

        # 个人 Skill
        if user_id:
            for skill_id in self._user_skills.get(user_id, []):
                if skill_id in self._skills:
                    candidates.append(self._skills[skill_id])

        # 团队 Skill
        if team_id:
            for skill_id in self._team_skills.get(team_id, []):
                if skill_id in self._skills:
                    candidates.append(self._skills[skill_id])

        # 过滤
        filtered = []
        for skill in candidates:
            if scope and skill.scope.value != scope:
                continue
            if category and skill.category.value != category:
                continue
            if status and skill.status.value != status:
                continue
            if min_rating and skill.rating < min_rating:
                continue
            filtered.append(skill)

        # 排序
        if sort_by == "usage":
            filtered.sort(key=lambda s: s.usage_count, reverse=True)
        elif sort_by == "rating":
            filtered.sort(key=lambda s: s.rating, reverse=True)
        elif sort_by == "quality":
            filtered.sort(key=lambda s: s.quality_score, reverse=True)
        elif sort_by == "created":
            filtered.sort(key=lambda s: s.created_at, reverse=True)

        # 分页
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "skills": [s.to_dict() for s in filtered[start:end]],
        }

    async def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        搜索 Skill

        Args:
            query: 搜索关键词
            user_id: 用户ID
            team_id: 团队ID
            top_k: 返回数量

        Returns:
            搜索结果列表
        """
        results = []

        # 获取可见的 Skill
        visible_skills = await self._get_visible_skills(user_id, team_id)

        query_lower = query.lower()

        for skill in visible_skills:
            score = 0.0
            match_reasons = []

            # 名称匹配
            if query_lower in skill.name.lower():
                score += 0.5
                match_reasons.append("名称匹配")

            # 描述匹配
            if query_lower in skill.description.lower():
                score += 0.3
                match_reasons.append("描述匹配")

            # 标签匹配
            for tag in skill.tags:
                if query_lower in tag.lower():
                    score += 0.2
                    match_reasons.append("标签匹配")
                    break

            # 触发词匹配
            for keyword in skill.trigger.keywords:
                if keyword.lower() in query_lower:
                    score += 0.3
                    match_reasons.append("触发词匹配")
                    break

            if score > 0:
                # 考虑质量分数
                score = score * 0.7 + skill.quality_score * 0.3
                results.append(SearchResult(
                    skill=skill,
                    score=score,
                    match_reason=", ".join(match_reasons),
                ))

        # 排序并返回
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    async def find_similar(
        self,
        name: str,
        description: str = "",
    ) -> List[SearchResult]:
        """
        查找相似的 Skill

        Args:
            name: Skill 名称
            description: 描述

        Returns:
            相似 Skill 列表
        """
        results = []

        for skill in self._skills.values():
            # 计算相似度
            name_sim = self._text_similarity(name, skill.name)
            desc_sim = self._text_similarity(description, skill.description)
            score = name_sim * 0.6 + desc_sim * 0.4

            if score > 0.5:
                results.append(SearchResult(
                    skill=skill,
                    score=score,
                    match_reason=f"名称相似度: {name_sim:.2f}",
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:5]

    def _text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度 (Jaccard)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    async def _get_visible_skills(
        self,
        user_id: Optional[str],
        team_id: Optional[str],
    ) -> List[Skill]:
        """获取用户可见的 Skill"""
        skills = []

        # 系统预设
        for skill in self._skills.values():
            if skill.scope == SkillScope.SYSTEM and skill.status == SkillStatus.ACTIVE:
                skills.append(skill)

        # 个人 Skill
        if user_id:
            for skill_id in self._user_skills.get(user_id, []):
                if skill_id in self._skills:
                    skill = self._skills[skill_id]
                    if skill.status in [SkillStatus.ACTIVE, SkillStatus.DRAFT]:
                        skills.append(skill)

        # 团队 Skill
        if team_id:
            for skill_id in self._team_skills.get(team_id, []):
                if skill_id in self._skills:
                    skill = self._skills[skill_id]
                    if skill.status == SkillStatus.ACTIVE:
                        skills.append(skill)

        return skills

    # ===== 推荐功能 =====

    async def recommend(
        self,
        query: str,
        intent: Optional[str] = None,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """
        推荐匹配的 Skill

        Args:
            query: 用户查询
            intent: 识别的意图
            user_id: 用户ID
            team_id: 团队ID
            top_k: 返回数量

        Returns:
            推荐 Skill 列表
        """
        visible_skills = await self._get_visible_skills(user_id, team_id)

        results = []
        query_lower = query.lower()

        for skill in visible_skills:
            # 检查触发条件
            if skill.trigger.matches(query, intent):
                score = skill.quality_score
                results.append(SearchResult(
                    skill=skill,
                    score=score,
                    match_reason="触发条件匹配",
                ))

        # 排序并返回
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    # ===== 执行记录 =====

    async def record_execution(
        self,
        skill_id: str,
        user_id: str,
        params: Dict[str, Any],
        success: bool,
        duration_ms: int,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> SkillExecution:
        """记录执行"""
        execution = SkillExecution(
            skill_id=skill_id,
            user_id=user_id,
            params=params,
            success=success,
            duration_ms=duration_ms,
            result=result,
            error=error,
        )

        self._executions[execution.id] = execution

        # 更新 Skill 统计
        skill = self._skills.get(skill_id)
        if skill:
            skill.usage_count += 1
            skill.last_used = datetime.now()
            if success:
                skill.success_count += 1
            else:
                skill.failure_count += 1

        return execution

    async def record_feedback(
        self,
        execution_id: str,
        score: int,
        comment: Optional[str] = None,
    ) -> bool:
        """记录反馈"""
        execution = self._executions.get(execution_id)
        if not execution:
            return False

        execution.feedback_score = score
        execution.feedback_comment = comment

        # 更新 Skill 评分
        skill = self._skills.get(execution.skill_id)
        if skill:
            # 滑动平均
            old_total = skill.rating * skill.rating_count
            skill.rating_count += 1
            skill.rating = (old_total + score) / skill.rating_count

        return True

    # ===== 生命周期管理 =====

    async def deprecate(self, skill_id: str, reason: str = "") -> bool:
        """弃用 Skill"""
        skill = self._skills.get(skill_id)
        if not skill:
            return False

        skill.status = SkillStatus.DEPRECATED
        skill.updated_at = datetime.now()
        logger.info(f"Deprecated skill: {skill_id}, reason: {reason}")
        return True

    async def archive(self, skill_id: str) -> bool:
        """归档 Skill"""
        skill = self._skills.get(skill_id)
        if not skill:
            return False

        skill.status = SkillStatus.ARCHIVED
        skill.updated_at = datetime.now()
        logger.info(f"Archived skill: {skill_id}")
        return True

    async def approve(self, skill_id: str) -> bool:
        """审核通过 (团队 Skill)"""
        skill = self._skills.get(skill_id)
        if not skill:
            return False

        skill.status = SkillStatus.ACTIVE
        skill.updated_at = datetime.now()
        logger.info(f"Approved skill: {skill_id}")
        return True

    def _increment_version(self, version: str) -> str:
        """递增版本号"""
        parts = version.split(".")
        if len(parts) == 3:
            patch = int(parts[2]) + 1
            return f"{parts[0]}.{parts[1]}.{patch}"
        return "1.0.1"

    # ===== 统计 =====

    async def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息"""
        skills = list(self._skills.values())

        if user_id:
            skills = [s for s in skills if s.owner == user_id]

        by_scope = {}
        by_category = {}
        by_status = {}

        for skill in skills:
            scope = skill.scope.value
            by_scope[scope] = by_scope.get(scope, 0) + 1

            category = skill.category.value
            by_category[category] = by_category.get(category, 0) + 1

            status = skill.status.value
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "total": len(skills),
            "by_scope": by_scope,
            "by_category": by_category,
            "by_status": by_status,
            "total_executions": len(self._executions),
            "avg_rating": sum(s.rating for s in skills if s.rating_count > 0) / max(len([s for s in skills if s.rating_count > 0]), 1),
        }


# 全局服务实例
_service: Optional[SkillService] = None


def get_skill_service() -> SkillService:
    """获取 Skill 服务实例"""
    global _service
    if _service is None:
        _service = SkillService()
    return _service
